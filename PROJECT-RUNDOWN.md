# Orqelis — Full Project Rundown

> **Single-file reference** for the entire repository: what it is, how it is structured, languages, packages, services, data model, APIs, docs, deploy, and what is / is not implemented.
>
> Product version: **0.1.0** (early development). Tagline: *Security for the Intelligent World.*

---

## 1. What this project is

**Orqelis** is an **AI-native cybersecurity platform** focused on **endpoint security** for Version 1.

A customer can:

1. Read the public marketing site and pricing  
2. Create an account and verify email  
3. Enter the customer dashboard  
4. Download and enroll a **Windows / macOS / Linux** security agent  
5. See devices and security telemetry  
6. Receive **rule-based detections** and **correlated incidents**  
7. Get **AI explanations** and remediation recommendations  
8. Approve or reject a small set of supported agent actions  
9. View a security report  

The endpoint agent collects **listed security telemetry only**. It does **not** execute arbitrary remote commands, open a remote shell, or act as a general remote-control tool.

### Explicit non-goals (not implemented)

| Area | Status |
| --- | --- |
| Web / API / cloud / code / mobile / network / identity security products | Not in V1 |
| Security Graph / attack paths | Not in V1 |
| Autonomous isolate / kill-process / credential revoke | Not in V1 |
| Marketplace | Not in V1 |
| Live Stripe/Paystack billing | Dev provider only |
| Signed MSI / pkg / deb / notarization | Needs vendor certs |
| ISO / SOC 2 claims | Not claimed |
| Archived APPI operator (voice, tools, remote RCE) | **Must not** be reused as the agent |

Legal docs still contain placeholders like `[LEGAL ENTITY NAME]` until the founder fills real entity data.

---

## 2. Languages & tech stack

| Layer | Language / runtime | Key libraries / frameworks |
| --- | --- | --- |
| Backend API | **Python 3.11+** (Docker image uses **3.12**) | FastAPI, Uvicorn, SQLAlchemy 2 (asyncio), Alembic, Pydantic Settings, PyJWT, bcrypt, httpx, pyotp |
| Detection engine | **Python** | Pure library (`orqelis_detection`) — deterministic rules, no LLM |
| AI gateway | **Python** | `orqelis_ai` — heuristic fallback or OpenAI-compatible HTTP (e.g. Groq) |
| Shared / security libs | **Python** | `orqelis_shared`, `orqelis_security` |
| Endpoint agent | **Python** | Same package for Win/macOS/Linux; platform collectors at runtime |
| Customer web + dashboard | **TypeScript / React / Next.js 15** | React 19, Tailwind CSS 4, Lucide icons, Playwright e2e |
| Founder admin console | **TypeScript / React / Next.js 15** | Port 3001 |
| Design tokens | **CSS** | `packages/ui/tokens.css` |
| Packaging / ops scripts | **PowerShell** + **Bash** | `scripts/*.ps1`, `scripts/*.sh` |
| Infra as config | **YAML / TOML / Dockerfile** | `docker-compose.yml`, `render.yaml`, `netlify.toml` |
| Docs | **Markdown** | Under `docs/` |

### Approximate source mix (by role)

- **Python**: API, agent, detection, AI, shared packages, tests  
- **TypeScript / TSX**: `apps/web`, `apps/admin`  
- **CSS**: globals + design tokens  
- **Markdown**: product, legal, security, compliance, internal docs  
- **Shell / PowerShell**: setup, packaging, PATH helpers  

There is **no** Go, Rust, Java, Kotlin, Swift, or Flutter app in this repo. macOS/Linux “agent apps” are packaging notes around the shared Python agent.

---

## 3. Top-level repository map

```
orqelis/
├── README.md                 # Quick start
├── PROJECT-RUNDOWN.md        # This file
├── .env.example              # Env template (copy → .env)
├── .gitignore
├── docker-compose.yml        # Optional Postgres + Redis + API
├── netlify.toml              # Website deploy (apps/web)
├── render.yaml               # API deploy (Render Blueprint)
│
├── apps/
│   ├── web/                  # Public site + customer dashboard (Next.js :3000)
│   ├── admin/                # Founder console (Next.js :3001)
│   ├── agent-windows/        # Cross-platform Python endpoint agent
│   ├── agent-macos/          # Packaging notes only
│   └── agent-linux/          # Packaging notes only
│
├── services/
│   ├── api/                  # FastAPI backend (main product brain)
│   ├── detection/            # Rule + correlation engine library
│   └── ai/                   # AI analysis gateway library
│
├── packages/
│   ├── shared/               # Enums, constants
│   ├── security/             # Passwords, tokens, crypto, redaction, rate limit
│   └── ui/                   # Design tokens (CSS)
│
├── docs/                     # Legal, compliance, security, product, customer, internal
├── infrastructure/
│   └── docker/
│       └── api.Dockerfile
└── scripts/                  # Dev setup + OS packaging
```

| Path | Role |
| --- | --- |
| `apps/web` | Marketing site + authenticated customer dashboard |
| `apps/admin` | Private founder / platform-admin console |
| `apps/agent-windows` | Endpoint agent (Windows, macOS, Linux collectors) |
| `apps/agent-macos` | macOS packaging notes |
| `apps/agent-linux` | Linux packaging notes |
| `services/api` | Versioned FastAPI backend (`/api/v1/*`) |
| `services/detection` | Deterministic detection + correlation |
| `services/ai` | AI roles (Sentinel, Hunter, Analyst, Auditor, Fixer) |
| `packages/shared` | Shared enums / schemas helpers |
| `packages/security` | Auth crypto, hashing, redaction, rate limiting |
| `packages/ui` | CSS design tokens |
| `docs/` | Legal, security, product, customer, internal docs |
| `scripts/` | Local setup and agent packaging |
| `infrastructure/` | Docker build for API |

---

## 4. Architecture (how pieces connect)

```
┌─────────────────┐     ┌──────────────────┐
│  apps/web       │     │  apps/admin      │
│  :3000          │     │  :3001           │
│  cookie session │     │  internal auth   │
└────────┬────────┘     └────────┬─────────┘
         │  orqelis_session      │  admin session
         └──────────┬────────────┘
                    ▼
         ┌──────────────────────┐
         │   services/api       │
         │   FastAPI :8000      │
         │   /health, /api/v1/* │
         └──────────┬───────────┘
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
 detection       AI gateway     DB (SQLite
 engine          (heuristic     or Postgres)
 (rules)         or LLM)
     ▲
     │ events via X-Orqelis-Device-Token
┌────┴─────────────────┐
│ apps/agent-windows   │
│ (Win / macOS / Linux)│
│ telemetry only       │
└──────────────────────┘
```

**Auth model**

- Humans (customers): `orqelis_session` **HTTP cookie**  
- Agents: `X-Orqelis-Device-Token` header  
- Founders: separate **internal** user/session tables (`InternalUser` / `InternalSession`)  
- Multi-tenant isolation: almost all customer data scoped by `organization_id`

**Data flow (security loop)**

1. Agent enrolls with one-time code → receives device token  
2. Agent heartbeats + posts event batches  
3. API persists events → runs detection → creates alerts / vulnerabilities / incidents  
4. High/critical alerts can auto-trigger Sentinel AI analysis  
5. Humans can request Fixer-style remediation recommendations  
6. Approvals gate only **`refresh_policy`** and **`restart_agent`**  
7. Agent polls/acks commands; audit log records sensitive actions  

PostgreSQL is the intended production store; **SQLite** is the default local/dev path. Redis is optional (rate-limit / coordination when `REDIS_URL` is set).

---

## 5. Apps in detail

### 5.1 `apps/web` — Public site + dashboard

| Item | Detail |
| --- | --- |
| Stack | Next.js 15 (Turbopack), React 19, TypeScript, Tailwind 4 |
| Port | `3000` |
| Package name | `orqelis-web` |
| E2E | Playwright (`e2e/smoke.spec.ts`, `e2e/register-dashboard.spec.ts`) |

**Public marketing / content routes**

| Route | Purpose |
| --- | --- |
| `/` | Landing |
| `/platform` | Platform overview |
| `/endpoint-security` | Endpoint product page |
| `/ai-security` | AI security team page |
| `/pricing` | Pricing |
| `/enterprise` | Enterprise |
| `/developers` | Developers |
| `/company` | Company |
| `/security` | Security trust page |
| `/docs` (+ privacy, terms, cookies, AUP, DPA, refund, disclosure) | Docs / legal mirrors |
| `/get-started` | Onboarding entry |
| `/login`, `/register`, `/verify-email`, `/reset-password` | Auth flows |

**Dashboard routes** (nav from `lib/nav.ts`)

| Route | Purpose |
| --- | --- |
| `/dashboard` | Overview / score |
| `/dashboard/devices`, `/dashboard/devices/[id]` | Devices + enroll |
| `/dashboard/alerts`, `/dashboard/alerts/[id]` | Alerts |
| `/dashboard/incidents`, `/dashboard/incidents/[id]` | Incidents |
| `/dashboard/vulnerabilities` | Posture / vuln findings |
| `/dashboard/ai` | AI Security Team |
| `/dashboard/reports` | Weekly / generated reports |
| `/dashboard/subscription` | Plans / activate (dev billing) |
| `/dashboard/settings` | Org / account settings |

**Key components / libs**

- `components/SiteChrome.tsx` — public chrome  
- `components/DashboardShell.tsx` — authenticated shell  
- `components/SecurityWidgets.tsx` — dashboard widgets  
- `components/Legal.tsx` — legal helpers  
- `lib/api.ts` — API client (cookie credentials, org header)  
- `lib/nav.ts` — nav + severity colors  

Env (via `.env` / `.env.local`): `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_ADMIN_URL`.

---

### 5.2 `apps/admin` — Founder console

| Item | Detail |
| --- | --- |
| Stack | Next.js 15, React 19, TypeScript, Tailwind 4 |
| Port | `3001` |
| Package name | `orqelis-admin` |

Shows **aggregated platform health** (counts, AI usage, agent versions, audit), **not** a dump of customer telemetry.

Bootstrap: set `FOUNDER_EMAIL` + `FOUNDER_PASSWORD` in root `.env` before starting the API (must be a normal domain email, not `@localhost`).

Files of note: `app/page.tsx`, `lib/api.ts`, `app/layout.tsx`, `app/globals.css`.

---

### 5.3 `apps/agent-windows` — Cross-platform endpoint agent

Despite the folder name, this is the **single Python agent** for all OSes.

| Item | Detail |
| --- | --- |
| Package | `orqelis_agent` (`python -m orqelis_agent`) |
| Commands | `enroll`, `run`, `status` |
| Auth | Device token after enroll |
| Behavior | Telemetry collection + limited command ack only |

**Module layout**

```
orqelis_agent/
├── __main__.py
├── cli.py            # argparse CLI + install notice
├── config.py         # local config / ORQELIS_API_URL
├── collect.py        # batch collection orchestration
├── common.py
├── transport.py      # HTTP client to API
└── platforms/
    ├── windows.py    # Security log, Defender, firewall, services
    ├── macos.py      # Gatekeeper, app firewall, unified log, launchctl
    └── linux.py      # auth.log/journal, ufw/firewalld, systemd
```

**Tests**: `tests/test_config.py`, `test_enroll_errors.py`, `test_notice.py`, `test_platforms.py`.

**Packaging**

- `scripts/package-windows.ps1`  
- `scripts/package-macos.sh`  
- `scripts/package-linux.sh`  

`apps/agent-macos` and `apps/agent-linux` hold README packaging notes only.

---

## 6. Services in detail

### 6.1 `services/api` — FastAPI backend

| Item | Detail |
| --- | --- |
| Package | `orqelis-api` |
| Entry | `app.main:app` |
| Version | `0.1.0` |
| Health | `GET /health` |

**App modules (`services/api/app/`)**

| File | Role |
| --- | --- |
| `main.py` | App factory, CORS, rate limit, security headers, router mount, founder bootstrap |
| `config.py` | Pydantic settings from env |
| `database.py` | Async SQLAlchemy engine / sessions |
| `models.py` | All ORM tables |
| `deps.py` | Auth / org dependency injection |
| `ingest.py` | Event ingest + detection pipeline hook |
| `scoring.py` | Org / risk scoring |
| `audit.py` | Audit log helpers |
| `emailer.py` | Log or SMTP email |
| `mfa.py` | TOTP MFA |
| `payments.py` | Dev subscription provider (not live Stripe) |
| `agent_downloads.py` | Agent download metadata for dashboard |
| `seed.py` | Reference plans / seed data |
| `routers/*` | HTTP API surface |

**Routers & API prefixes**

| Router | Prefix | Responsibilities |
| --- | --- | --- |
| `auth` | `/api/v1/auth` | Register, login, logout, me, MFA, verify email, password reset, sessions |
| `organizations` | `/api/v1/organizations` | Current org, security score |
| `devices` | `/api/v1/devices` | List/detail, enrollments, revoke, agent downloads |
| `agent` | `/api/v1/agent` | Enroll, heartbeat, events, policy, command ack |
| `events` | `/api/v1/events` | List tenant events |
| `alerts` | `/api/v1/alerts` | List / detail |
| `incidents` | `/api/v1/incidents` | List / detail / status |
| `vulnerabilities` | `/api/v1/vulnerabilities` | List |
| `ai` | `/api/v1/ai` | Analyze + list analyses |
| `reports` | `/api/v1/reports` | List / generate (+ digest email path) |
| `approvals` | `/api/v1` | Approvals + actions recommend/decide |
| `policies` | `/api/v1/policies` | Collection policy |
| `subscription` | `/api/v1/subscription` | Plans + activate |
| `demo` | `/api/v1/demo` | Labeled demo workspace (never mixed with live agents) |
| `admin` | `/api/v1/admin` | Founder login, overview, audit, system incidents |

**Migrations**: Alembic under `services/api/alembic/`

- `0001_initial.py`  
- `0002_demo_workspaces.py`  

Locally `AUTO_MIGRATE=true` can create schema via `init_db()`.

**API tests** (`services/api/tests/`): auth, MFA, tenancy, detection, scoring, redaction, approvals, admin billing, demo UX, AI config, deploy config, OS detections, health, etc. Run:

```powershell
cd services\api
python -m pytest
```

---

### 6.2 `services/detection` — Rule engine

| Item | Detail |
| --- | --- |
| Package | `orqelis_detection` |
| Core | `orqelis_detection/engine.py` → `DetectionEngine` |

**Principles**

- Deterministic; **LLMs are not used** in detection  
- Extension hooks exist for baseline / anomaly / threat-intel providers (null stubs by default)

**Example rule families** (from engine)

- Auth failure bursts  
- Fail-then-success  
- Privileged account creation  
- Security control changes  
- Suspicious process markers (encoded PowerShell, `mshta`, `regsvr32`, etc.)  
- Unusual outbound  
- Posture → vulnerability findings  
- Correlation: multiple high-value rules on same device → incident  

---

### 6.3 `services/ai` — AI gateway

| Item | Detail |
| --- | --- |
| Package | `orqelis_ai` |
| Core | `orqelis_ai/gateway.py` → `AIGateway` |

**Roles**

| Role | Purpose |
| --- | --- |
| `sentinel` | Triage alerts |
| `hunter` | Search provided telemetry for patterns |
| `analyst` | Incident investigation timeline / root cause |
| `auditor` | Posture / config review |
| `fixer` | Defensive remediation only (no offensive advice) |

**Providers**

- Default: **`heuristic`** (local structured explanation, no API key)  
- Optional: OpenAI-compatible HTTP (`AI_PROVIDER`, `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`) — e.g. Groq in `render.yaml`  
- Inputs are **redacted** via `orqelis_security.redaction` before model calls  

---

## 7. Shared packages

### 7.1 `packages/shared` (`orqelis_shared`)

- `enums.py` — customer roles, device status, event categories, severities, incident statuses, approval/action statuses, agent command kinds, subscription statuses, email backends  
- `constants.py` — shared constants  

**Agent command kinds allowed in product:** `refresh_policy`, `restart_agent` only.

### 7.2 `packages/security` (`orqelis_security`)

| Module | Role |
| --- | --- |
| `passwords.py` | bcrypt hashing |
| `tokens.py` | Token helpers / JWT-related |
| `crypto.py` | Encryption helpers (`ENCRYPTION_KEY`) |
| `redaction.py` | PII / secret redaction before AI |
| `rate_limit.py` | In-memory rate limiter used by API |

### 7.3 `packages/ui`

- `tokens.css` — design tokens shared / referenced by frontends  

---

## 8. Data model (database tables)

Defined in `services/api/app/models.py`:

| Table / model | Purpose |
| --- | --- |
| `users` | Customer accounts (password hash, MFA, lockout, terms) |
| `organizations` | Tenants |
| `memberships` | User ↔ org roles |
| `sessions` | Customer cookie sessions |
| `email_tokens` | Verify / reset tokens |
| `login_attempts` | Auth audit / lockout signals |
| `internal_users` | Founder console accounts |
| `internal_sessions` | Founder sessions |
| `plans` | Subscription plan catalog |
| `subscriptions` | Per-org subscription (dev provider) |
| `devices` | Enrolled endpoints |
| `device_enrollments` | One-time enroll codes |
| `agent_versions` | Tracked agent builds |
| `policies` | Collection / heartbeat policy |
| `events` | Security telemetry (`SecurityEvent`) |
| `alerts` | Detections |
| `incidents` | Correlated cases |
| `incident_events` | Incident linkage |
| `vulnerabilities` | Posture findings |
| `approval_requests` | Human gate for actions |
| `actions` | Recommended / approved actions |
| `agent_commands` | Queued commands to devices |
| `ai_analyses` | Stored AI outputs |
| `ai_usage` | Token / cost tracking |
| `reports` | Generated markdown reports |
| `integrations` | Stub / available integrations |
| `audit_logs` | Platform / tenant audit trail |
| `system_incidents` | Platform-level incidents (admin) |
| `demo_workspaces` | Marks labeled demo orgs (no mix with live agents) |

---

## 9. Documentation tree (`docs/`)

| Area | Files |
| --- | --- |
| **Legal** | `terms-of-service`, `privacy-policy`, `acceptable-use-policy`, `cookie-policy`, `data-processing-agreement`, `refund-policy`, `subscription-terms`, `security-terms`, `security-sla`, `subprocessor-policy`, `vulnerability-disclosure-policy` |
| **Compliance** | `information-security-policy`, `access-control-policy`, `data-retention-policy`, `data-deletion-policy`, `incident-response-policy` |
| **Security** | `security-overview`, `security-architecture`, `threat-model`, `secure-development-policy`, `secrets-management`, `logging-monitoring` |
| **Product** | `product-overview`, `endpoint-security` |
| **Customer** | `getting-started`, `endpoint-agent-guide` |
| **Developer** | `getting-started` |
| **Internal** | `architecture`, `completion-matrix`, `founder-console`, `ideas-and-next-bets` |

These are V0.1.0 drafts; replace legal placeholders before public publication.

---

## 10. Scripts & infrastructure

### Scripts (`scripts/`)

| Script | Purpose |
| --- | --- |
| `dev-setup.ps1` | Install editable Python packages + npm deps |
| `start-dev.ps1` | Helper to start local stack |
| `env-path.ps1` | Fix PATH for `python` / `node` in Cursor terminals |
| `package-windows.ps1` | Windows agent package |
| `package-macos.sh` | macOS agent package |
| `package-linux.sh` | Linux agent package |

### Docker / compose

- `docker-compose.yml`: optional `postgres:16`, `redis:7`, and `api` service  
- `infrastructure/docker/api.Dockerfile`: slim Python 3.12 image installing security → shared → detection → ai → api  

**Local default:** no Docker. Use SQLite (`DATABASE_URL=sqlite+aiosqlite:///./orqelis.db`) and empty `REDIS_URL`.

### Hosted deploy

| Piece | Host | Config |
| --- | --- | --- |
| Website + dashboard | **Netlify** | `netlify.toml` → base `apps/web`, Node 20 |
| API | **Render** | `render.yaml` Docker blueprint, health `/health` |

Production must set long `JWT_SECRET` / `ENCRYPTION_KEY`, `COOKIE_SECURE=true`, Postgres `DATABASE_URL`, and matching `CORS_ORIGINS` / `APP_BASE_URL` / `PUBLIC_API_URL`.

---

## 11. Configuration (environment)

Copy `.env.example` → `.env`. Important variables:

| Variable | Role |
| --- | --- |
| `DATABASE_URL` | SQLite (dev) or `postgresql+asyncpg://...` |
| `REDIS_URL` | Optional |
| `JWT_SECRET` | Session / JWT secret (long random in prod) |
| `ENCRYPTION_KEY` | Encrypt MFA secrets etc. |
| `CORS_ORIGINS` | Allowed web origins |
| `ENVIRONMENT` | `development` / `production` |
| `AUTO_MIGRATE` | Schema bootstrap |
| `APP_BASE_URL` / `ADMIN_BASE_URL` | Frontend URLs |
| `COOKIE_SECURE` | HTTPS cookies in prod |
| `SMTP_*` / `EMAIL_BACKEND` | Email (`log` or `smtp`) |
| `AI_PROVIDER` / `AI_API_KEY` / `AI_BASE_URL` / `AI_MODEL` | AI gateway |
| `FOUNDER_EMAIL` / `FOUNDER_PASSWORD` | Bootstrap founder (dev) |
| `NEXT_PUBLIC_*` | Browser-visible web URLs |
| `PUBLIC_API_URL` / `ORQELIS_API_URL` | Public API for agent enroll commands |

**Never commit** `.env`, real API keys, or production secrets (`.gitignore` covers `.env`, `*.db`, `node_modules`, `.next`, egg-info, agent data dirs, etc.).

---

## 12. Local development (quick reference)

**Prerequisites:** Python 3.11+, Node.js 20+. Docker optional.

```powershell
cd orqelis
copy .env.example .env

python -m pip install -e .\packages\security
python -m pip install -e .\packages\shared
python -m pip install -e .\services\detection
python -m pip install -e .\services\ai
python -m pip install -e .\services\api\[dev]
python -m pip install -e .\apps\agent-windows\[dev]

cd apps\web; npm install
cd ..\admin; npm install
```

**Run**

```powershell
# API
cd services\api
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Web
cd apps\web
npm run dev

# Admin
cd apps\admin
npm run dev -- --port 3001

# Agent (after dashboard enrollment code)
cd apps\agent-windows
python -m orqelis_agent enroll --code 123456 --api http://127.0.0.1:8000
python -m orqelis_agent run
```

---

## 13. Completion status (honest)

From `docs/internal/completion-matrix.md`:

### Done in V1 / V2 (local)

- Public site, pricing, docs  
- Register, verify email, login/logout, lockout, sessions  
- TOTP MFA  
- Dev subscription activate (no live charge)  
- Win / macOS / Linux agent enroll + telemetry  
- Rule detection + incident correlation  
- OS-aware firewall / Gatekeeper-style findings  
- Auto Sentinel on high/critical alerts  
- Manual AI Security Team roles  
- Approve `refresh_policy` / `restart_agent` only  
- Weekly report + digest email (log or SMTP)  
- Founder console aggregates / audit  
- Labeled demo ingest (refuses mix with live agents)  
- Pytest suite for API  

### Not done yet

- Signed / notarized OS installers  
- Live Stripe / Paystack billing  
- V3/V4 platform (Security Graph, multi-domain products, autonomous defense, marketplace)  

---

## 14. Security posture (product design constraints)

- Tenant isolation by `organization_id`  
- Agent is telemetry-only; no arbitrary remote execution  
- Only two agent command kinds after human approval  
- AI sees redacted payloads; no AI keys in browser or agent  
- Rate limiting + request size caps + security response headers on API  
- Production refuses weak `JWT_SECRET` / `ENCRYPTION_KEY`  
- Demo workspaces are explicitly labeled and kept separate from live agent data  
- MFA (TOTP), session revoke, account lockout after failed logins  

---

## 15. Mental model (one paragraph)

Orqelis is a **monorepo cybersecurity SaaS**: Next.js frontends talk to a Python FastAPI core; enrolled endpoints push telemetry through a shared Python agent; a deterministic detection library turns events into alerts/incidents; an AI gateway explains and recommends (never detects alone); humans approve only two safe agent actions; shared Python packages own crypto/enums; Markdown docs cover legal and security; Netlify + Render (or local SQLite) deploy the two main surfaces.

---

## 16. File inventory (source-focused)

Omits caches, egg-info, lockfile noise where repetitive. Use this as a map of “what matters.”

### Root

- `README.md`, `PROJECT-RUNDOWN.md`, `.env.example`, `.gitignore`
- `docker-compose.yml`, `netlify.toml`, `render.yaml`

### `apps/web`

- `package.json`, `next.config.ts`, `tsconfig.json`, `postcss.config.mjs`, `playwright.config.ts`
- `app/**/page.tsx` (marketing + auth + dashboard pages)
- `app/layout.tsx`, `app/globals.css`, `app/dashboard/layout.tsx`
- `components/*.tsx`, `lib/api.ts`, `lib/nav.ts`
- `e2e/*.spec.ts`

### `apps/admin`

- `package.json`, `next.config.ts`, `app/page.tsx`, `app/layout.tsx`, `app/globals.css`, `lib/api.ts`

### `apps/agent-windows`

- `pyproject.toml`, `orqelis_agent/**`, `tests/**`, `README.md`

### `apps/agent-macos`, `apps/agent-linux`

- `README.md` only (packaging notes)

### `services/api`

- `pyproject.toml`, `alembic.ini`, `alembic/**`
- `app/main.py`, `config.py`, `database.py`, `models.py`, `deps.py`, …
- `app/routers/*.py`
- `tests/*.py`

### `services/detection`

- `pyproject.toml`, `orqelis_detection/engine.py`

### `services/ai`

- `pyproject.toml`, `orqelis_ai/gateway.py`

### `packages/*`

- `shared/orqelis_shared/{enums,constants}.py`
- `security/orqelis_security/{passwords,tokens,crypto,redaction,rate_limit}.py`
- `ui/tokens.css`

### `docs/**`

- Legal, compliance, security, product, customer, developer, internal markdown

### `scripts/**`, `infrastructure/docker/api.Dockerfile`

---

*Generated as a living rundown of the Orqelis monorepo at version 0.1.0. Prefer updating this file when major folders or product scope change.*
