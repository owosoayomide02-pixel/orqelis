# Deploy Orqelis today (Vercel + Render)

## Architecture

- **Vercel** → `apps/web` (signup, login, dashboard, AI roles UI)
- **Render** → API Docker image (`infrastructure/docker/api.Dockerfile`) with Hunter tools + AI gateway
- **Postgres** → Render Postgres (or any `DATABASE_URL`)

AI roles already in product: **Sentinel / Hunter / Analyst / Auditor / Fixer** (verify domain → Hunter scan → findings → Analyst/Fixer per finding → Auditor report).

Hunter chain (authorized domains only): **subfinder → httpx → nmap → nuclei** (no Metasploit / Wi‑Fi).

---

## 1) Render API

1. New Web Service → Docker → this repo  
   Dockerfile: `infrastructure/docker/api.Dockerfile` · Context: repo root  
2. Add **Postgres** and copy `DATABASE_URL`  
3. Set env:

| Key | Value |
|-----|--------|
| `ENVIRONMENT` | `production` |
| `COOKIE_SECURE` | `true` |
| `AUTO_MIGRATE` | `true` |
| `JWT_SECRET` | long random |
| `ENCRYPTION_KEY` | long random |
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` |
| `APP_BASE_URL` | `https://YOUR-APP.vercel.app` |
| `PUBLIC_API_URL` | `https://YOUR-API.onrender.com` |
| `AI_PROVIDER` | `groq` |
| `AI_API_KEY` | your Groq key |
| `AI_BASE_URL` | `https://api.groq.com/openai/v1` |
| `AI_MODEL` | `openai/gpt-oss-20b` |
| `AI_MODEL_LIGHT` | same or cheaper model |
| `AI_MODEL_HEAVY` | same or stronger model |
| `SCANNER_MODE` | `local` (Option A on Render) |

First build is slow (nuclei templates) — expected.

Health: `GET https://YOUR-API.onrender.com/health`

---

## 2) Vercel web

1. Import repo → Root Directory: **`apps/web`**  
2. Env:

| Key | Value |
|-----|--------|
| `NEXT_PUBLIC_APP_URL` | `https://YOUR-APP.vercel.app` |
| `NEXT_PUBLIC_API_URL` | `https://YOUR-API.onrender.com` |

3. Deploy. Open site → **Register** / **Login** → **Web Assets**.

---

## 3) Smoke test after deploy

1. Register a tenant  
2. Add a domain you own → DNS TXT verify  
3. On the asset page, roles are on top: **Sentinel · Hunter · Analyst · Auditor · Fixer**  
4. Run **Hunter** → wait for findings (subfinder → httpx → nmap → nuclei)  
5. Use **Analyst** / **Fixer** on a finding; **Auditor** for report  
6. Confirm Sentinel auto notes on high/critical (auto-detected)  
7. Home **Download for Windows** → login → Devices (agent / enroll commands)

AI gateway roles (with prompts): sentinel, hunter, hunter_analysis, analyst, auditor, fixer.

---

## Option B (later)

If Render free tier is too weak for scans, run `scanner-service/` on a VM and set:

```
SCANNER_MODE=remote
SCANNER_SERVICE_URL=http://VM:9000
SCANNER_INTERNAL_TOKEN=shared-secret
```
