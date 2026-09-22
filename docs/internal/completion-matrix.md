# V1 / V2 completion cross-check

This is the honest status after the finish-the-product pass. V3 and V4 from `orqelis_phases.md` are **not implemented**. They are a later platform (Security Graph, nine domains, autonomous actions, marketplace).

## Version 1 success condition

| Step | Status |
| --- | --- |
| Public site, pricing, docs | Done |
| Register, verify email, login, logout, lockout, sessions | Done |
| TOTP MFA enroll / login challenge | Done |
| Dev subscription activate (no live charge) | Done |
| Windows / macOS / Linux agent enroll + telemetry | Done |
| Rule detection + incident correlation | Done |
| OS-aware firewall / Gatekeeper findings | Done |
| Auto Sentinel on high/critical alerts | Done |
| Manual AI Security Team roles | Done |
| Approve refresh_policy / restart_agent only | Done |
| Weekly report + digest email (log or SMTP) | Done |
| Founder console: counts, AI usage, agent versions, audit, no customer telemetry dump | Done |
| Labeled demo ingest, refuses mix with live agents | Done |
| Pytest | Run locally (`cd services/api; python -m pytest`) |

## Version 2 (real, local)

| Item | Status |
| --- | --- |
| MFA TOTP | Done |
| Digest email on report generate | Done (SMTP if configured, otherwise API log) |
| Deeper OS-specific detection titles | Done |
| Agent retry on failed transport | Done |
| Signed MSI / pkg / deb / notarization | **Not done** — needs vendor signing certificates |
| Live Stripe/Paystack billing | **Not done** — no production payment keys; development provider only |

## Not in this product yet (V3/V4)

Security Graph, attack paths, web/API/cloud/code/mobile/network/identity products, marketplace, autonomous isolate / kill-process / credential revoke, ISO/SOC 2 claims.

Legal placeholders (`[LEGAL ENTITY NAME]`, etc.) stay until the founder fills real entity data.
