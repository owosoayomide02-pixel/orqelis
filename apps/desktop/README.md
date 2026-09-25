# Orqelis Desktop (Tauri static bundle)

The Windows `.exe` packages the statically exported `apps/web/out` UI. It does **not** load a remote URL.

## Prerequisites

- Rust toolchain
- WebView2 (Windows 10/11)
- `NEXT_PUBLIC_API_URL` pointing at the hosted API (required for static export)

## Build

```bash
cd apps/web
# ensure NEXT_PUBLIC_API_URL is set for the API host
cd ../desktop
npm install
npm run tauri:build
```

Outputs: `src-tauri/target/release/bundle/msi/` and `nsis/`.

## Auth

Desktop uses `POST /api/v1/auth/desktop-login` + Bearer tokens (see Part 6.6). Refresh tokens must be stored via OS secure storage in production; sessionStorage is acceptable only for local testing.

## Code signing

Set `bundle.windows.certificateThumbprint` after purchasing an Authenticode cert. Generate updater keys with `tauri signer generate` before public releases.
