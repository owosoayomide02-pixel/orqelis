#!/bin/bash
# Runs inside the Kali scanner container.
set -euo pipefail
DOMAIN="${TARGET_DOMAIN:?TARGET_DOMAIN required}"
OUT=/scan/out
mkdir -p "$OUT"

# Filter hosts that resolve to private/link-local ranges (SSRF defense)
filter_hosts() {
  python3 - <<'PY'
import ipaddress, socket, sys
hosts = [h.strip() for h in sys.stdin if h.strip()]
public = []
for host in hosts:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        continue
    bad = False
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast:
            bad = True
            break
    if not bad and infos:
        public.append(host)
print("\n".join(public))
PY
}

RAW_SUB=""
RAW_HTTP=""
RAW_NUC=""

if command -v subfinder >/dev/null 2>&1; then
  RAW_SUB=$(timeout 120 subfinder -d "$DOMAIN" -json -silent 2>/dev/null || true)
  echo "$RAW_SUB" > "$OUT/subfinder.jsonl"
else
  RAW_SUB=$(printf '{"host":"%s"}\n' "$DOMAIN")
fi

HOSTS=$(echo "$RAW_SUB" | sed -n 's/.*"host":"\([^"]*\)".*/\1/p')
if [ -z "$HOSTS" ]; then HOSTS="$DOMAIN"; fi
HOSTS=$(echo "$HOSTS" | filter_hosts || true)

if [ -n "$HOSTS" ]; then
  if command -v httpx >/dev/null 2>&1; then
    RAW_HTTP=$(echo "$HOSTS" | timeout 60 httpx -json -silent 2>/dev/null || true)
  elif command -v httpx-toolkit >/dev/null 2>&1; then
    RAW_HTTP=$(echo "$HOSTS" | timeout 60 httpx-toolkit -json -silent 2>/dev/null || true)
  else
    RAW_HTTP=""
  fi
  echo "$RAW_HTTP" > "$OUT/httpx.jsonl"
fi

URLS=$(echo "${RAW_HTTP:-}" | sed -n 's/.*"url":"\([^"]*\)".*/\1/p')
if [ -n "$URLS" ] && command -v nuclei >/dev/null 2>&1; then
  RAW_NUC=$(echo "$URLS" | timeout 300 nuclei -json -severity medium,high,critical -silent 2>/dev/null || true)
  echo "$RAW_NUC" > "$OUT/nuclei.jsonl"
fi

python3 - <<'PY' || true
import json, os
out = {
  "tools_run": ["subfinder", "httpx", "nuclei"],
  "raw_output": {
    "subfinder": open("/scan/out/subfinder.jsonl").read() if os.path.exists("/scan/out/subfinder.jsonl") else "",
    "httpx": open("/scan/out/httpx.jsonl").read() if os.path.exists("/scan/out/httpx.jsonl") else "",
    "nuclei": open("/scan/out/nuclei.jsonl").read() if os.path.exists("/scan/out/nuclei.jsonl") else "",
  },
  "status": "completed",
  "error_message": None,
}
open("/scan/out/result.json","w").write(json.dumps(out))
PY
