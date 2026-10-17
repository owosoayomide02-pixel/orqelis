# Deploy Orqelis (Vercel + Railway)

## Architecture

- **Vercel** → `apps/web` (signup, login, dashboard, AI roles UI)
- **Railway** → API Docker image (`infrastructure/docker/api.Dockerfile`) with Hunter tools + AI gateway
- **PostgreSQL** → Railway Postgres (or another reachable PostgreSQL service)

AI roles already in product: **Sentinel / Hunter / Analyst / Auditor / Fixer** (verify domain → Hunter scan → findings → Analyst/Fixer per finding → Auditor report).

Hunter chain (authorized domains only): **subfinder → httpx → tlsx → katana → gobuster → nikto → nmap → nuclei** (no Metasploit / Wi‑Fi).

---

## 1) Railway API

1. Create a Railway project from this GitHub repository. Set the API service's **Root Directory** to the repository root.
2. Add a PostgreSQL service to the project.
3. In the API service variables, set `RAILWAY_DOCKERFILE_PATH=infrastructure/docker/api.Dockerfile`. The Dockerfile reads Railway's injected `$PORT` and binds to `0.0.0.0`.
4. Set `DATABASE_URL=${{Postgres.DATABASE_URL}}` (replace `Postgres` with the exact PostgreSQL service name if different). The API converts PostgreSQL URLs to the async `asyncpg` driver format.
5. Configure the API service's health check path as `/health`, then add:

| Key | Value |
|-----|--------|
| `ENVIRONMENT` | `production` |
| `COOKIE_SECURE` | `true` |
| `AUTO_MIGRATE` | `true` |
| `JWT_SECRET` | long random secret |
| `ENCRYPTION_KEY` | long random secret |
| `CORS_ORIGINS` | frontend's HTTPS origin |
| `APP_BASE_URL` | frontend's HTTPS URL |
| `ADMIN_BASE_URL` | admin frontend URL, if deployed |
| `PUBLIC_API_URL` | public HTTPS URL generated for the Railway API service |
| `AI_PROVIDER` | `nvidia` |
| `NVIDIA_API_KEY` | your NVIDIA NIM API key |
| `OPENROUTER_API_KEY` | your OpenRouter API key (optional fallback) |
| `AI_MODEL` | `meta/llama-3.3-70b-instruct` |
| `AI_BASE_URL` | leave empty to use the selected provider's API endpoint |
| `EMAIL_BACKEND` | `smtp` when production email is configured |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | credentials and sender supplied by your mail provider |
| `SCANNER_MODE` | `local` |
| `SCANNER_ENABLE_FFUF` | `true` |
| `SCANNER_ENABLE_WAPITI` | `true` |
| `FOUNDER_EMAIL`, `FOUNDER_PASSWORD` | optional initial founder account credentials |

Railway provides `PORT` to the container; do not hard-code a separate public port. Use the Railway PostgreSQL service's private `DATABASE_URL` reference and keep API and database in the same Railway project/region. The Docker build installs the scanner binaries and templates; builds can take several minutes and require successful access to upstream package and GitHub release sources.

NVIDIA NIM is the primary provider (`https://integrate.api.nvidia.com/v1`). OpenRouter is the fallback when configured. Provider calls require a valid model entitlement and incur separate provider usage charges. Use a persistent Railway service plan appropriate for the scanner workload and enable PostgreSQL backups.

Health: `GET https://YOUR-RAILWAY-API-DOMAIN/health`

---

## 2) Frontend

Deploy the web frontend to Vercel (Root Directory: **`apps/web`**) or another static/frontend host. Set:

| Key | Value |
|-----|--------|
| `NEXT_PUBLIC_APP_URL` | frontend's HTTPS URL |
| `NEXT_PUBLIC_API_URL` | public HTTPS URL generated for the Railway API service |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | only if customer Supabase Auth is enabled |

Include the exact frontend origin in the Railway API's `CORS_ORIGINS`. Deploy, then open the site → **Register** / **Login** → **Web Assets**.

---

## 3) Smoke test after deploy

1. Register and verify a tenant account; confirm terms/privacy consent and email delivery.
2. Enter a domain you own or are explicitly authorized to assess; sign in.
3. Choose **Hunter** and any supported follow-up tasks in the workspace.
4. Add the presented DNS TXT record; scanning must remain blocked until ownership verification succeeds.
5. Confirm the terminal completes and routes to findings; test **Analyst**, **Fixer** (draft only), and **Auditor**.
6. Verify account recovery, session expiry/revocation, rate limits, logs, backups, and restore procedures.

Local automated tests use an in-memory database and mock scanner. They do not test a real DNS provider, live scan tools, email provider, or live AI API. Validate those integrations in a controlled staging environment using an owned domain and monitored provider budgets before production.

AI gateway roles (with prompts): sentinel, hunter, hunter_analysis, analyst, auditor, fixer.

---

## Option B (later)

For a separate scanner host, run `scanner-service/` on a VM and set:

```
SCANNER_MODE=remote
SCANNER_SERVICE_URL=http://VM:9000
SCANNER_INTERNAL_TOKEN=shared-secret
```
