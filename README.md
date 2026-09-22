# Orqelis

**Security for the Intelligent World.**

Orqelis is an AI-native cybersecurity platform. Version **0.1.0** is an early development release: Windows, macOS, and Linux endpoint security, a detection engine, AI-assisted analysis, a customer dashboard, and a private founder console.

It is **not** production-ready. Features described in later roadmaps (web/API/cloud/code/mobile/network/identity security, Security Graph, autonomous defense) are extension points only and are not implemented.

This repository is a new product. The archived APPI operator (voice, tools, remote command execution) is **not** part of Orqelis and must not be reused as the endpoint agent.

## Version 1 scope

A customer can:

1. Read the public site and pricing
2. Create an account and verify email
3. Enter the dashboard
4. Download and enroll a Windows, macOS, or Linux security agent
5. See the device and security telemetry
6. Receive rule-based detections and correlated incidents
7. Get AI explanations and remediation recommendations
8. Approve or reject supported actions
9. View a security report

The agent collects listed security telemetry only. It does **not** execute arbitrary remote commands.

## Repository

| Path | Role |
| --- | --- |
| `apps/web` | Public website and customer dashboard |
| `apps/admin` | Founder / admin console |
| `apps/agent-windows` | Endpoint agent (Windows/macOS/Linux collectors) |
| `apps/agent-macos` | macOS packaging notes |
| `apps/agent-linux` | Linux packaging notes |
| `services/api` | Versioned FastAPI backend |
| `services/detection` | Rule and correlation engine |
| `services/ai` | AI gateway |
| `packages/shared` | Shared enums and schemas |
| `packages/security` | Password hashing, tokens, redaction |
| `packages/ui` | Design tokens |
| `docs/` | Legal, security, product, and customer documentation |

## Prerequisites

- Python 3.11+ (the `py` launcher is enough if `python` opens the Microsoft Store)
- Node.js 20+
- Docker is **not required**. Local development uses SQLite. Redis stays empty.

## Setup

Or use `scripts/dev-setup.ps1` after Python 3.11+ and Node.js 20+ are installed. If a new Cursor terminal still cannot see `python` or `node`, run `. .\scripts\env-path.ps1` first, or restart Cursor so PATH updates apply.

```powershell
cd orqelis
copy .env.example .env

python -m pip install -e .\packages\security
python -m pip install -e .\packages\shared
python -m pip install -e .\services\detection
python -m pip install -e .\services\ai
python -m pip install -e .\services\api\[dev]
python -m pip install -e .\apps\agent-windows\[dev]

cd apps\web
npm install
cd ..\admin
npm install
cd ..\..
```

Leave `DATABASE_URL=sqlite+aiosqlite:///./orqelis.db` and `REDIS_URL=` empty. That is the no-Docker setup.

PostgreSQL is optional later. Only if you install Docker:

```powershell
docker compose up -d postgres redis
```

Then set `DATABASE_URL=postgresql+asyncpg://orqelis:orqelis@localhost:5432/orqelis` in `.env`.

## Run

API:

```powershell
cd services\api
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Website / dashboard:

```powershell
cd apps\web
npm run dev
```

Founder console:

```powershell
cd apps\admin
npm run dev -- --port 3001
```

Endpoint agent (after creating an enrollment code in the dashboard). The same commands work on Windows, macOS, and Linux:

```powershell
cd apps\agent-windows
python -m orqelis_agent enroll --code 123456 --api http://127.0.0.1:8000
python -m orqelis_agent run
```

Packaged OS builds: `scripts/package-windows.ps1`, `scripts/package-macos.sh`, `scripts/package-linux.sh`.

## Deploy

Website and API are separate.

1. **API** — Render Blueprint (`render.yaml`) or Docker (`infrastructure/docker/api.Dockerfile`). Health check: `GET /health`.
2. **Website** — Netlify (`netlify.toml`, base `apps/web`). Set `NEXT_PUBLIC_APP_URL` to the Netlify URL and `NEXT_PUBLIC_API_URL` to the Render API URL so `/api/*` rewrites stay same-origin for cookies.
3. On the API set `ENVIRONMENT=production`, `COOKIE_SECURE=true`, `CORS_ORIGINS` and `APP_BASE_URL` to the Netlify URL, `PUBLIC_API_URL` to the Render URL, Postgres `DATABASE_URL`, and long `JWT_SECRET` / `ENCRYPTION_KEY`.
4. Enroll agents with `ORQELIS_API_URL=https://YOUR-API.onrender.com`.

## Tests

```powershell
cd services\api
python -m pytest
```

## Security

Never commit API keys, tokens, or production configuration. See `docs/security/` and `.env.example`.
