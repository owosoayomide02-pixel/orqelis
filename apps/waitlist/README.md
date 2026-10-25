# Orqelis Waitlist

This is a standalone waitlist website, separate from the main Orqelis site. Deploy `apps/waitlist` as its own Vercel project and assign it a dedicated domain such as `waitlist.orqelis.com`.

The waitlist privacy notice is available at `/privacy` and identifies Owoso Ayomide as the operator, with a business location in Osun State, Nigeria. The support inbox is `support@waitlist.orqelis.dev`. Review the notice against actual provider configurations and applicable requirements before publishing. Scanner scope and intended safety controls are described at `/about-scanner`.

The waitlist page includes indicative pricing copied from the main site's proposed plans. Billing is not live, and the plans and limits may change before launch. Competitor pricing notes link to the public vendor pages reviewed for the comparison.

## Deploy to Vercel

1. Import this repository as a new Vercel project.
2. Set the project root directory to `apps/waitlist`.
3. Add `WAITLIST_API_URL` pointing to the deployed Orqelis API origin, for example `https://orqelis-api-production.up.railway.app`.
4. Deploy and assign the waitlist's own domain in Vercel's project settings.

The waitlist app forwards submissions server-to-server to `/api/v1/waitlist`. It does not need a browser-to-API CORS exception, and it does not need Resend credentials. The API requires its own PostgreSQL database and Resend environment (`RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and optional `RESEND_WAITLIST_NOTIFICATION_EMAIL`). The API adds contacts globally in Resend, so no audience or segment ID is required; the key needs both Contacts: Write and email-sending permissions.

## Local development

Set `WAITLIST_API_URL` in `apps/waitlist/.env.local` to `http://127.0.0.1:8000`, start the API, then run:

```powershell
cd apps\waitlist
npm install
npm run dev
```

Open `http://localhost:3000`.
