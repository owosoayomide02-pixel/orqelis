# Orqelis Scanner Service (Option B)

Standalone Hunter VM — **not** deployed to Render/Vercel. Run on a separate host
(e.g. Oracle Cloud free tier). Restrict inbound TCP **9000** to Render's outbound
IPs only; always require `SCANNER_INTERNAL_TOKEN`.

## Build & run

```bash
cd scanner-service
docker build -t orqelis-scanner-service .
docker run --rm -p 9000:9000 \
  -e SCANNER_INTERNAL_TOKEN='long-random-secret' \
  orqelis-scanner-service
```

## API

- `GET /health`
- `POST /run-scan?domain=example.com` with header `x-internal-token: <token>`

## Wire to Orqelis API (Render)

On the API service set:

```
SCANNER_MODE=remote
SCANNER_SERVICE_URL=http://YOUR_VM_PRIVATE_OR_PUBLIC_IP:9000
SCANNER_INTERNAL_TOKEN=same-secret-as-above
```

Keep Option A (`SCANNER_MODE=local`) available as fallback if the VM is down.
