# Architecture

Customer dashboard and public site (`apps/web`) and founder console (`apps/admin`) call `services/api`.

The Windows agent authenticates with `X-Orqelis-Device-Token`. Humans authenticate with the `orqelis_session` cookie.

Events are stored per `organization_id`. `services/detection` applies deterministic rules and correlation. `services/ai` explains findings after redaction.

PostgreSQL is the intended store; SQLite is a local/dev fallback. Redis is optional coordination.
