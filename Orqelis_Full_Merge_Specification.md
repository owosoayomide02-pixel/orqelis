# Orqelis — Full Merge Specification
### Web Asset Scanning + AI Role Workflow + Windows Native Shell

This is a complete technical specification, not a summary. Treat it as the source of truth for the build. Where it conflicts with older scaffolding, this document wins — the concept (below) is fixed; the implementation is free to be rebuilt from scratch to support it.

---

## PART 0 — THE CONCEPT (do not deviate from this)

Orqelis is a unified security platform with two asset types feeding one pipeline:

1. **Devices** — endpoint agents (Windows/macOS/Linux) reporting telemetry (already exists, keep as-is)
2. **Web Assets** — domains a user adds and verifies ownership of, which can be scanned

For a Web Asset, the user chooses which **AI role** acts on it:

| Role | What it does | Backend action |
|---|---|---|
| **Sentinel** | Passive monitoring, auto-triggers on high/critical findings | Watches events, no scan of its own |
| **Hunter** | Active reconnaissance/vulnerability scan | Runs Kali tools (subfinder, httpx, nuclei, nmap) in a sandbox against the verified domain |
| **Analyst** | Explains a specific finding in plain language | LLM call, no scanning |
| **Auditor** | Compiles findings into a client-facing report (PDF) | LLM call + PDF render |
| **Fixer** | Drafts a remediation (code diff, config change) for a finding | LLM call only — never touches Kali, never auto-applies |

Findings from Hunter's scans flow into the **same** detection/correlation/alert system already used for device telemetry. One AI provider, one API key, multiple roles = multiple prompts against the same model.

Windows gets a native `.exe`. It is a **thin shell** (Tauri) wrapping the same web frontend — it is not a separate app with separate logic, and it does not bundle Python or Flutter.

---

## PART 1 — DATA MODEL (complete field-level spec)

### 1.1 `web_assets` table

```python
class WebAsset(Base):
    __tablename__ = "web_assets"

    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    organization_id: UUID = Column(UUID, ForeignKey("organizations.id"), nullable=False, index=True)
    domain: str = Column(String, nullable=False)  # e.g. "acme-app.com" — no protocol, no path
    verification_status: str = Column(String, default="unverified")  # unverified | verified | verification_failed
    verification_method: str = Column(String, default="dns_txt")
    verification_token: str = Column(String, nullable=False, default=lambda: secrets.token_hex(16))
    verified_at: datetime | None = Column(DateTime, nullable=True)
    created_by_user_id: UUID = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    archived: bool = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "domain", name="uq_org_domain"),
    )
```

**Validation rules:**
- `domain` must pass a strict regex (`^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$`), lowercase-normalized on save
- Reject IP addresses and private/internal ranges (10.x, 192.168.x, 127.x, etc.) at creation — this is a domain-scanning product, not an internal network tool, and scanning internal ranges is an SSRF risk vector
- Reject domains already `verified` under a *different* organization (prevents one org squatting/scanning a domain another org has already proven ownership of)

### 1.2 `scan_jobs` table

```python
class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    web_asset_id: UUID = Column(UUID, ForeignKey("web_assets.id"), nullable=False, index=True)
    organization_id: UUID = Column(UUID, ForeignKey("organizations.id"), nullable=False, index=True)
    role: str = Column(String, nullable=False, default="hunter")  # currently only "hunter" triggers a scan
    status: str = Column(String, default="queued")  # queued | running | completed | failed | timed_out
    tools_run: list[str] = Column(JSON, default=list)  # ["subfinder", "httpx", "nuclei"]
    raw_output: dict = Column(JSON, nullable=True)  # per-tool raw output, trimmed before AI ingestion
    error_message: str | None = Column(String, nullable=True)
    requested_by_user_id: UUID = Column(UUID, ForeignKey("users.id"), nullable=False)
    started_at: datetime | None = Column(DateTime, nullable=True)
    completed_at: datetime | None = Column(DateTime, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

### 1.3 Reuse existing event/alert tables

Do **not** create a parallel findings table. The existing detection engine already consumes an event shape from device telemetry — extend that shape with a `source` discriminator:

```python
# Existing event shape (device), extend with:
source: str  # "device" | "web_asset"
source_id: UUID  # device_id OR web_asset_id, depending on source
```

Every finding a scan produces should be inserted as a row in the existing events table with `source="web_asset"` and `source_id=web_asset.id`, then run through the existing detection engine unmodified. If the current schema hard-codes `device_id` as a required foreign key, migrate it to the polymorphic `source`/`source_id` pair above — this is a breaking migration, write it as an Alembic revision with a data-backfill step that sets `source="device"` and `source_id=device_id` for all existing rows.

---

## PART 2 — API ENDPOINTS (complete request/response contracts)

All routes under `/api/v1`, all require the existing `orqelis_session` cookie auth, all scoped to the caller's `organization_id`.

### 2.1 `POST /web-assets`

Request:
```json
{ "domain": "acme-app.com" }
```

Response `201`:
```json
{
  "id": "uuid",
  "domain": "acme-app.com",
  "verification_status": "unverified",
  "verification_instructions": {
    "record_type": "TXT",
    "record_name": "_orqelis-verify.acme-app.com",
    "record_value": "orqelis-verify=3f9a2b1c8e7d4f6a"
  }
}
```

Errors: `400` invalid domain format, `409` domain already registered (own org — return existing record instead of erroring, idempotent create), `403` domain verified under another org.

### 2.2 `POST /web-assets/{id}/verify`

No body. Server performs a live DNS TXT lookup on `_orqelis-verify.<domain>`, checks for a record matching `orqelis-verify=<token>`.

Response `200` (success):
```json
{ "id": "uuid", "verification_status": "verified", "verified_at": "2026-09-26T10:00:00Z" }
```

Response `200` (not yet found — not an error, DNS propagation takes time):
```json
{ "id": "uuid", "verification_status": "unverified", "message": "TXT record not found yet. DNS changes can take up to 24 hours to propagate." }
```

Rate-limit this endpoint per web_asset (e.g. max once per 30 seconds) to avoid hammering DNS resolvers.

### 2.3 `POST /web-assets/{id}/scan`

Request:
```json
{ "role": "hunter" }
```

**Server-side gate (non-negotiable):** return `403` if `web_asset.verification_status != "verified"`. This check happens in the endpoint handler itself, not only in the frontend.

Response `202`:
```json
{ "scan_job_id": "uuid", "status": "queued" }
```

Errors: `403` not verified, `429` a scan is already running for this asset (one concurrent scan per asset), `429` organization scan quota exceeded (tie into existing plan/tier limits).

### 2.4 `GET /web-assets/{id}/scans/{scan_job_id}`

Response `200`:
```json
{
  "id": "uuid",
  "status": "completed",
  "tools_run": ["subfinder", "httpx", "nuclei"],
  "findings_count": 7,
  "started_at": "...",
  "completed_at": "..."
}
```

Frontend polls this every 3-5 seconds while `status` is `queued` or `running`.

### 2.5 `GET /web-assets/{id}/findings`

Returns events with `source="web_asset"` and `source_id=id`, same shape/pagination as the existing device-alerts list endpoint. Reuse that serializer.

### 2.6 AI role endpoints

**`POST /findings/{finding_id}/analyze`** (Analyst role)
```json
// request: {}
// response 200:
{
  "explanation": "This SSH version has a known remote code execution vulnerability (CVE-2023-4813)...",
  "severity_assessment": "critical",
  "confidence": 0.91
}
```

**`POST /findings/{finding_id}/fix`** (Fixer role)
```json
// response 200:
{
  "fix_type": "config_change",
  "description": "Update nginx configuration to add missing CSP header",
  "diff": "--- a/nginx.conf\n+++ b/nginx.conf\n@@ ...",
  "requires_human_approval": true
}
```

This response is stored, never auto-applied. If a PR-generation integration exists (GitHub App), the endpoint that actually opens a PR is a **separate, explicit** action: `POST /findings/{finding_id}/fix/open-pr`, requiring the fix to already exist and a human to have clicked an explicit "Open as PR" button — never triggered automatically.

**`POST /web-assets/{id}/report`** (Auditor role)
```json
// response 202 (report generation is async, PDF rendering takes a few seconds):
{ "report_job_id": "uuid", "status": "queued" }
```

---

## PART 3 — HUNTER SCAN RUNNER (the Kali integration)

### 3.1 Sandboxing

Every scan runs inside a fresh, disposable Docker container — never on the host running `services/api`.

```dockerfile
# infrastructure/docker/scanner.Dockerfile
FROM kalilinux/kali-rolling
RUN apt-get update && apt-get install -y subfinder httpx-toolkit nuclei nmap
WORKDIR /scan
ENTRYPOINT ["/scan/run.sh"]
```

The container receives the target domain as an environment variable, runs its tool chain, writes results to a mounted volume as JSON, and exits. The host process (`services/api` background worker) waits for exit, reads the output volume, then destroys the container. No network access from the container beyond what's needed to reach the target (use Docker's default bridge network, not host networking).

### 3.2 Execution order and per-tool timeout

```python
SCAN_SEQUENCE = [
    {"tool": "subfinder", "args": ["-d", domain, "-json"], "timeout_s": 120},
    {"tool": "httpx", "args": ["-json"], "timeout_s": 60, "stdin_from": "subfinder"},
    {"tool": "nuclei", "args": ["-json", "-severity", "medium,high,critical"], "timeout_s": 300, "stdin_from": "httpx"},
]
```

Each subprocess call:
```python
import subprocess

def run_tool(cmd: list[str], timeout_s: int, stdin_data: str | None = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise ScanTimeoutError(f"{cmd[0]} exceeded {timeout_s}s")
```

If any tool in the chain times out or exits non-zero, mark the `ScanJob` as `failed` (or `timed_out`) with `error_message` set, and do not proceed to the next tool. Partial results already gathered (e.g. subfinder succeeded, nuclei timed out) should still be saved and surfaced — don't discard successful partial work.

### 3.3 Output normalization

Each tool's raw output format is different. Write one parser per tool, all producing the same normalized shape before insertion into the events table:

```python
class NormalizedFinding(TypedDict):
    title: str
    description: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    tool_source: str          # "nuclei", "httpx", etc.
    raw_reference: dict       # trimmed raw tool output for this specific finding, for AI context
    evidence: str | None      # e.g. matched request/response snippet

def parse_nuclei_line(line: str) -> NormalizedFinding:
    data = json.loads(line)
    return NormalizedFinding(
        title=data["info"]["name"],
        description=data["info"].get("description", ""),
        severity=data["info"]["severity"],
        tool_source="nuclei",
        raw_reference={"template-id": data["template-id"], "matched-at": data["matched-at"]},
        evidence=data.get("matcher-status"),
    )
```

`subfinder` output (subdomain discovery) generally isn't a "finding" on its own — it's input to the next stage (`httpx` probes each discovered subdomain). Only persist subfinder/httpx output as findings if they reveal something notable (e.g. an unexpected exposed subdomain, an outdated server header) — don't create a database row per subdomain discovered with nothing wrong.

### 3.4 Cost control before AI ingestion

Before sending findings to the AI gateway, trim `raw_reference` to the minimum needed for the model to reason about the finding — do not send full raw JSON blobs from every tool. A finding sent to the AI gateway should be under ~200 tokens of context per finding; batch multiple findings into one prompt rather than one API call per finding where the role allows it (e.g. Sentinel's initial triage can process a whole scan's findings in one call).

---

## PART 4 — AI GATEWAY EXTENSION

### 4.1 One provider, role-specific prompts

`services/ai/orqelis_ai/gateway.py` already has provider config (`AI_PROVIDER`, `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`). Do not add new provider config for web-asset roles. Add role-specific system prompts as constants:

```python
ROLE_PROMPTS = {
    "sentinel": "You are Sentinel, a security triage assistant. Given a batch of findings, identify which require immediate escalation...",
    "hunter_analysis": "You are Hunter, interpreting raw scan output. Given normalized findings from a domain scan, explain what each means in plain language and assign a real-world exploitability score...",
    "analyst": "You are Analyst. Given a single finding, explain it to a technical but non-specialist reader...",
    "auditor": "You are Auditor. Given a list of findings for a domain, write a client-facing report section. Tone: professional, direct, not alarmist...",
    "fixer": "You are Fixer. Given a finding, propose a concrete remediation as a diff or config change. Do not suggest anything that requires infrastructure you cannot see. Flag if manual investigation is needed instead of a direct fix...",
}
```

### 4.2 Structured output enforcement

All roles must return valid JSON matching a defined schema — use the model provider's structured-output/JSON-mode feature if available (both Claude and OpenAI-compatible APIs support this). Validate the response against a Pydantic model before persisting; on validation failure, retry once with an explicit "your last response was invalid JSON, return only valid JSON matching this schema: ..." correction prompt. On second failure, mark the AI call as failed and surface a "analysis unavailable, retry" state to the user rather than persisting malformed data.

### 4.3 Model routing (cost-tiering, optional but recommended)

```python
MODEL_FOR_ROLE = {
    "sentinel": os.environ.get("AI_MODEL_LIGHT", "gpt-4o-mini"),
    "hunter_analysis": os.environ.get("AI_MODEL_HEAVY", "claude-sonnet-4-6"),
    "analyst": os.environ.get("AI_MODEL_HEAVY", "claude-sonnet-4-6"),
    "auditor": os.environ.get("AI_MODEL_HEAVY", "claude-sonnet-4-6"),
    "fixer": os.environ.get("AI_MODEL_HEAVY", "claude-sonnet-4-6"),
}
```

This still uses one `AI_API_KEY` if the provider supports multiple models on one key (true for OpenAI-compatible gateways and for Anthropic). Only add a second key if you deliberately want to split spend across two providers.

---

## PART 5 — FRONTEND (`apps/web`)

### 5.1 New routes

| Route | Purpose |
|---|---|
| `/dashboard/web-assets` | List of domains, verification status badges, "Add domain" button |
| `/dashboard/web-assets/new` | Domain input form → shows DNS TXT instructions on submit |
| `/dashboard/web-assets/[id]` | Detail view: verification status, role selector, scan history, findings list |
| `/dashboard/web-assets/[id]/report` | Rendered Auditor report, download-as-PDF button |

### 5.2 Components (new, under `apps/web/components/web-assets/`)

- `DomainForm.tsx` — input + client-side format validation before hitting the API
- `VerificationInstructions.tsx` — shows the TXT record to add, a "Check now" button calling the verify endpoint, polls automatically every 10s while unverified and the tab is focused
- `RoleSelector.tsx` — five buttons/cards (Sentinel/Hunter/Analyst/Auditor/Fixer), disabled state for all except Sentinel until `verification_status === "verified"`
- `ScanProgress.tsx` — polls `GET /web-assets/{id}/scans/{scan_job_id}` every 3-5s, shows which tool is currently running if the backend exposes that granularity, else a generic progress state
- `FindingsList.tsx` — reuse the existing device-alerts list component if its props can accept a `source` discriminator instead of forking a new component
- `FixSuggestion.tsx` — shows Fixer's diff with syntax highlighting, "Open as PR" button (only if GitHub integration exists), explicit "this has not been applied" note

### 5.3 API client (`lib/api.ts`)

Add typed functions matching Part 2's contracts exactly:
```typescript
export async function createWebAsset(domain: string): Promise<WebAsset> { ... }
export async function verifyWebAsset(id: string): Promise<WebAsset> { ... }
export async function startScan(id: string, role: "hunter"): Promise<{ scan_job_id: string; status: string }> { ... }
export async function getScanStatus(webAssetId: string, scanJobId: string): Promise<ScanJob> { ... }
export async function getFindings(webAssetId: string): Promise<Finding[]> { ... }
export async function analyzeFinding(findingId: string): Promise<AnalystResult> { ... }
export async function fixFinding(findingId: string): Promise<FixerResult> { ... }
export async function generateReport(webAssetId: string): Promise<{ report_job_id: string }> { ... }
```

Reuse the existing `orqelis_session` cookie-based fetch wrapper already used elsewhere in `lib/api.ts` — do not introduce a separate auth mechanism for these calls.

---

## PART 6 — WINDOWS NATIVE APP (Tauri, STATIC BUNDLE MODE — read carefully, this is not a browser wrapper)

**This is the critical distinction for this section: the frontend code itself is compiled and packaged INSIDE the `.exe`. It does not load a remote URL. It behaves like VS Code / Cursor — install it, it runs locally, it only calls the backend over HTTP for data. If a future engineer changes this to load a remote URL instead of the local static build, that is a regression of this spec, not an equivalent implementation.**

### 6.1 Why static bundle, not remote-load

| | Remote-load shell (rejected) | Static bundle (this spec) | Electron (VS Code/Cursor) |
|---|---|---|---|
| Where frontend code lives | On the server only | Packaged inside the `.exe` | Packaged inside the `.exe` |
| Works if server is slow/down | No — blank/broken window | Yes — UI loads instantly, only API calls fail gracefully | Yes |
| Install size | ~3-5MB | ~10-25MB | ~150-250MB |
| Rendering engine | System WebView2 | System WebView2 | Bundled Chromium |
| Feels like a "real app" | No — feels like a bookmark | Yes | Yes |

Static bundle gets the exact "real app" feel of Electron-based tools, at a fraction of the size, because it reuses the WebView2 runtime already installed on Windows 10/11 instead of shipping a private copy of Chromium.

### 6.2 Prerequisite: `apps/web` must support static export

Next.js App Router apps with server-side rendering, API routes, or middleware **cannot** be statically exported as-is. Before touching Tauri, audit `apps/web` for:

- Any `app/api/*` route handlers — these must be removed from the exported build; all data must come from `services/api`, never from a Next.js server function, since there is no Next.js server running inside the desktop app
- Any use of `middleware.ts` for auth redirects — must be replaced with client-side auth checks (check session/token in a `useEffect` or route guard component, redirect client-side), since middleware requires a running Node server and static export has none
- Any dynamic route that currently relies on server-side data fetching (`getServerSideProps` equivalent / server components doing DB calls directly) — must be converted to client-side fetching against `services/api`, since the desktop bundle has no backend of its own

Add to `apps/web/next.config.ts`:
```typescript
const nextConfig = {
  output: "export",
  images: { unoptimized: true }, // static export can't use Next's image optimization server
};
```
Run `npm run build` and confirm a static `out/` directory is produced with no build errors about dynamic server usage. **Do this audit and fix pass before starting the Tauri scaffold below** — Tauri cannot work around a frontend that still expects a Node server.

### 6.3 Scaffold

```bash
cd apps
npm create tauri-app@latest desktop -- --template react-ts
cd desktop
```

This creates `apps/desktop/` as a new workspace member, with `src-tauri/` holding the Rust shell and `src/` initially holding a placeholder frontend — replace that placeholder by pointing the build at the statically exported `apps/web/out` directory instead of building a second copy of the frontend.

### 6.4 Directory layout after scaffold

```
apps/desktop/
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── build.rs
│   ├── icons/
│   │   ├── icon.ico
│   │   └── icon.png
│   └── src/
│       └── main.rs
├── package.json          # build script copies apps/web/out into here before tauri build
└── (no separate src/ frontend — the bundled frontend IS apps/web/out)
```

### 6.5 `tauri.conf.json` — full annotated config

```json
{
  "build": {
    "beforeBuildCommand": "cd ../web && npm run build",
    "beforeDevCommand": "cd ../web && npm run build",
    "devPath": "../web/out",
    "distDir": "../web/out"
  },
  "tauri": {
    "allowlist": {
      "http": {
        "all": false,
        "scope": ["https://api.orqelis.com/*"]
      },
      "shell": { "all": false },
      "fs": {
        "all": false,
        "scope": ["$APPDATA/orqelis/*"],
        "readFile": true,
        "writeFile": true,
        "createDir": true
      },
      "notification": { "all": true }
    },
    "bundle": {
      "identifier": "com.orqelis.desktop",
      "icon": ["icons/icon.ico", "icons/icon.png"],
      "resources": [],
      "targets": ["msi", "nsis"],
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    },
    "security": {
      "csp": "default-src 'self'; connect-src 'self' https://api.orqelis.com; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    },
    "windows": [
      {
        "title": "Orqelis",
        "width": 1280,
        "height": 800,
        "minWidth": 960,
        "minHeight": 640,
        "resizable": true,
        "fullscreen": false,
        "center": true
      }
    ],
    "updater": {
      "active": true,
      "endpoints": ["https://api.orqelis.com/desktop/updates/{{target}}/{{current_version}}"],
      "dialog": true,
      "pubkey": "REPLACE_WITH_GENERATED_UPDATER_PUBLIC_KEY"
    }
  }
}
```

**Notes on every non-obvious field:**
- `"devPath"` / `"distDir"` point at the **built static export**, not a dev server URL — this is what makes it bundle-based instead of remote-load
- `allowlist.http.scope` restricts outbound HTTP to only your API domain — the bundled frontend cannot be redirected to call arbitrary URLs even if compromised by injected content
- `allowlist.fs.scope` restricted to an app-specific data folder (`$APPDATA/orqelis/`) — used for local cache/offline queue (Part 6.8), not general filesystem access
- `security.csp` — a real Content-Security-Policy, same principle as a web app's CSP, enforced by the WebView2 engine itself
- `updater` block enables **auto-updates** — critical for a bundled app, since users won't get new features just by refreshing a browser tab like the web version does; every release must publish an update manifest to the endpoint above

### 6.6 Auth — this DOES need real rework (unlike the rejected remote-load version)

Because the frontend now runs from a local file bundle (`asset://` origin inside WebView2), not from `https://app.orqelis.com`, **cookies set by `services/api` for the `app.orqelis.com` domain will not be sent automatically** — cookie scoping is origin-based, and the desktop app's origin is not that domain. This is the single most important technical change from the rejected shell approach.

Required changes to `services/api`:

1. Add a new auth endpoint: `POST /api/v1/auth/desktop-login` — accepts email/password (or existing MFA flow), returns a **JWT access token + refresh token pair** in the response body (not as a cookie)
2. Add `POST /api/v1/auth/desktop-refresh` — accepts a refresh token, returns a new access token
3. All existing `/api/v1/*` routes must accept **either** the existing `orqelis_session` cookie (web) **or** an `Authorization: Bearer <token>` header (desktop) — add this as a shared auth dependency that checks both, does not break existing web behavior

Required changes to the bundled frontend (`apps/web`, built specifically for the `output: "export"` static build):
1. Detect desktop context: `const isDesktop = typeof window !== "undefined" && "__TAURI__" in window;`
2. When `isDesktop`, use the token-based login/refresh endpoints above instead of the cookie-based ones, and store tokens using Tauri's secure storage plugin (`tauri-plugin-store` or OS keychain via `tauri-plugin-keyring`) — **never** `localStorage` for the refresh token, since that's plain-text on disk
3. API client wrapper (`lib/api.ts`) must branch: attach `Authorization: Bearer` header when `isDesktop`, rely on cookie when not — same functions, one added header logic path, not a forked API client

### 6.7 Build script (`apps/desktop/package.json`)

```json
{
  "scripts": {
    "prebuild": "cd ../web && npm run build",
    "tauri:dev": "tauri dev",
    "tauri:build": "npm run prebuild && tauri build"
  }
}
```

### 6.8 Offline behavior (this is what "real app" actually buys you)

Since the UI shell loads instantly from local files regardless of network state, define explicit behavior for API-unreachable states rather than leaving it undefined:

- On app launch, attempt a lightweight `GET /health` against `services/api`. If unreachable, show a persistent but non-blocking banner ("Offline — showing cached data") rather than a broken UI
- Cache the last-fetched dashboard summary, device list, and web-asset list to local storage (via the `fs` allowlist scope set in 6.5, writing to `$APPDATA/orqelis/cache.json`) so the app has *something* to show immediately on launch before the network round-trip completes, then refreshes in place once the API responds
- Actions requiring the network (starting a scan, approving a fix) must be disabled with a clear tooltip when offline, not silently fail

### 6.9 Code signing and distribution

- Unsigned `.msi`/`.exe` builds trigger Windows SmartScreen ("Windows protected your PC") on first run — acceptable for internal testing, not for real distribution
- Purchase an Authenticode code-signing certificate (OV or EV; EV avoids SmartScreen reputation delay but costs significantly more) from a CA (DigiCert, Sectigo)
- Set `bundle.windows.certificateThumbprint` in `tauri.conf.json` once a cert is installed in the Windows cert store on the build machine, or sign as a post-build step in CI using `signtool.exe`
- Generate the updater keypair (`tauri signer generate`) before shipping v1 publicly — retrofitting the updater after users already have unsigned/unupdatable installs is painful; set it up now even if the first few releases are manual

### 6.10 Build & output

```bash
cd apps/desktop
npm run tauri:build
```
Outputs under `apps/desktop/src-tauri/target/release/bundle/msi/` and `.../bundle/nsis/`. Expected size range for this static-bundle approach: **10-25MB**, versus the 150MB+ an Electron equivalent of the same app would produce — same "real bundled app" behavior, far smaller footprint, because WebView2 (already on the user's system) replaces a private Chromium copy.

---

## PART 7 — SECURITY / SCOPE ENFORCEMENT CHECKLIST

- [ ] Domain format validated server-side, private/internal IP ranges rejected
- [ ] Scan endpoint returns `403` if `verification_status != "verified"` — checked in the handler, not just hidden in the UI
- [ ] One concurrent scan per `web_asset` enforced (reject with `429` if one is already `running`)
- [ ] Scan containers have no host network access, no access to other containers, destroyed after each run
- [ ] Every scan and every AI call logged with `organization_id`, `user_id`, timestamp — audit trail, same pattern as existing device-action audit log
- [ ] Fixer output never auto-applied; PR-opening is a separate explicit action gated on human click
- [ ] Rate limits on `/verify` (DNS lookup abuse) and `/scan` (per-org quota tied to pricing tier)

---

## PART 8 — TESTING PLAN

- **Unit:** each tool-output parser (Part 3.3) tested against saved sample outputs (record real `nuclei`/`httpx`/`subfinder` JSON output as fixtures)
- **Unit:** domain validation rejects IPs, internal ranges, malformed strings
- **Integration:** full flow against a test container — create web asset → mock DNS verify (stub the DNS lookup in test mode) → trigger scan against a deliberately vulnerable test target (e.g. a local `DVWA` or `juice-shop` container) → assert findings land in the events table with `source="web_asset"`
- **Integration:** AI gateway calls mocked in CI (no real API spend in tests) — assert schema validation catches malformed mock responses
- **E2E (Playwright):** add-domain → verification-instructions-shown → (test-mode auto-verify) → select Hunter → scan-progress-shown → findings-rendered

---

## PART 9 — ENVIRONMENT VARIABLES (additions)

| Variable | Role |
|---|---|
| `SCANNER_DOCKER_IMAGE` | Tag of the built scanner container (Part 3.1) |
| `SCAN_TIMEOUT_TOTAL_S` | Hard ceiling for a full scan job, independent of per-tool timeouts |
| `AI_MODEL_LIGHT` / `AI_MODEL_HEAVY` | Optional cost-tiering model names (Part 4.3) — falls back to `AI_MODEL` if unset |
| `SCAN_QUOTA_PER_ORG_MONTHLY` | Enforced in the scan endpoint, tied to the org's pricing tier |
| `DNS_VERIFY_RATE_LIMIT_SECONDS` | Minimum seconds between verify attempts per web asset |

---

## PART 10 — DESIGN SYSTEM (extends `packages/ui/tokens.css`, do not fork a new one)

The existing repo already has `packages/ui/tokens.css` as the shared design-token file consumed by both `apps/web` and `apps/admin`. This section extends that file — it does not replace it or create a parallel styling system. Every new component built for Web Assets (Part 5) must consume these tokens, not hardcoded colors/spacing.

### 10.1 Visual direction — "terminal-meets-editorial"

Dark-first, monospace for technical data, clean sans for structure and headlines. Findings should read as an active discovery, not a static spreadsheet. Two color registers exist within one system:

```css
/* packages/ui/tokens.css — additions */

:root {
  /* Base surfaces */
  --surface-0: #0A0B0D;       /* app background */
  --surface-1: #14161A;       /* card background */
  --surface-2: #1C1F24;       /* nested/inset elements */
  --border: #2A2E35;
  --border-strong: #3A3F47;

  /* Text */
  --text-primary: #F2F3F5;
  --text-secondary: #A8ADB6;
  --text-muted: #6B7078;

  /* Security-audit register (sharp, urgent) */
  --fill-danger: #E24B4A;
  --bg-danger: #2A1616;
  --text-danger: #F0817F;
  --fill-warning: #E2A63D;
  --bg-warning: #2A2416;
  --text-warning: #F0C77E;

  /* Performance/UX-audit register (cooler, optimistic) — reserved for when Part 9's Puppeteer engine ships */
  --fill-info: #4B9FE2;
  --bg-info: #16232A;
  --text-info: #7FC0F0;
  --fill-success: #4BE28A;
  --bg-success: #16291F;
  --text-success: #7FF0AA;

  /* Accent (brand, used sparingly — CTAs, active states, not decoration) */
  --accent: #D85A30;
  --accent-hover: #E86A3E;

  /* Typography */
  --font-sans: "Inter", -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", "SF Mono", Consolas, monospace;

  /* Spacing scale (4px base) */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
  --space-4: 16px; --space-6: 24px; --space-8: 32px;

  --radius: 8px;
  --radius-lg: 12px;
}

/* Light mode override — respect system preference, do not force dark-only */
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --surface-0: #FAFAFA;
    --surface-1: #FFFFFF;
    --surface-2: #F2F3F5;
    --border: #E2E4E8;
    --text-primary: #14161A;
    --text-secondary: #4A4F58;
    --text-muted: #8A8F98;
  }
}
```

### 10.2 Typography rules

- Headlines, nav, buttons, body copy → `--font-sans`
- Anything technical: domains, IPs, CVE IDs, code diffs, JSON, timestamps, hashes → `--font-mono`, always, no exceptions — this is what makes the product feel authored by security people rather than a generic SaaS template
- Never use a third typeface. Weight and size create hierarchy, not font-switching.

### 10.3 Motion — signals "this is live," not decoration

Every async/monitoring surface should use restrained motion to communicate "actively watching," matching the two mockups already built and approved earlier in this project (`orqelis_security_audit_mockup`, `orqelis_animated_scan_hero`):

- Scan-in-progress: a moving scanline within the target's bounding box (see approved mockup), never a generic spinner alone
- New finding arriving: slide-in + fade, staggered by ~120-150ms per item if multiple arrive in one batch — never all findings appearing simultaneously, since simultaneous appearance reads as "static list," not "live detection"
- Risk score: animates by counting up from 0 to the actual value over ~1.2-1.5s on first render, not an instant jump
- Respect `prefers-reduced-motion: reduce` — disable all of the above (render final state immediately) when set; this is an accessibility requirement, not optional polish

### 10.4 Component states (define all of these explicitly — do not ship only the "happy path" visual)

Every data-bearing component (findings list, scan progress, device list, report view) needs an explicit design for:
- **Empty** — no domains added yet / no findings yet. Not a blank white space — a short instructional message + primary CTA ("Add your first domain")
- **Loading** — skeleton screens matching the final layout's shape, not a centered spinner replacing the whole page
- **Error** — network/API failure, phrased in plain language, with a retry action, never a raw stack trace or error code shown to the customer
- **Offline** (desktop app specific, see Part 6.8) — persistent non-blocking banner, cached content still visible

### 10.5 Why this matters for retention specifically (answering "people should come back")

Visual polish alone does not make someone open an app repeatedly — the design has to support behaviors that create a reason to return. This repo already has two features that directly drive this; make sure they're visually prominent, not buried:

- **Weekly report + digest email** (already implemented per the completion matrix) — this is the actual retention engine. The email should link directly into the specific dashboard view it summarizes, and that destination view should visually highlight "what changed since last week" (new findings, resolved findings, risk score delta) at the top, not require the user to hunt for what's new
- **Sentinel auto-triggering on high/critical alerts** — when this fires, it should be visually distinct from a manually-requested Analyst explanation (e.g. a small "auto-detected" tag), so users learn to trust that the system is watching even when they're not actively looking, which is what brings someone back rather than only visiting on a fixed schedule
- **Risk score as the front-and-center number** on both the dashboard home and any email/notification — a single trackable number people can watch trend down over time is a stronger return-driver than a list of findings, because it gives a "did my number improve" reason to check back in, similar to how a credit-score app or a fitness-tracker score creates a checking habit

Do not add streaks, gamification badges, or artificial engagement mechanics — those fit a consumer habit app, not a security tool a business owner is trusting with real findings. The professionalism this product needs comes from restraint, correctness, and the "live monitoring" motion language above — not from consumer-app engagement patterns bolted on.

---

## NON-GOALS (explicit — do not build these in this pass)

- No Puppeteer/performance-audit engine yet — Hunter/Kali only
- No autonomous remediation — Fixer proposes, never applies
- No Flutter anywhere
- No new AI provider/second API key — one key, role-tiered models at most
- No changes to the existing endpoint-agent (`apps/agent-windows`) logic or protocol
- No bundling Python or a local backend into the Windows shell — it stays a thin client hitting the hosted API
