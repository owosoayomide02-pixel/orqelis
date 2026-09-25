import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Developers"
      kicker="API V1"
      lead="Human APIs use session cookies. Agent APIs use a device token header. They are not interchangeable. Versioned routes live under /api/v1/."
      aside={
        <>
          <ContentCard title="Auth models">
            <p>
              <strong className="text-[var(--fg)]">Humans:</strong> browser session cookie after login.
            </p>
            <p className="mt-2">
              <strong className="text-[var(--fg)]">Agents:</strong> device token on enrollment — never reuse for dashboard calls.
            </p>
          </ContentCard>
          <ContentCard title="Docs in repo">
            <p>Customer and developer guides live in the repository docs/ directory alongside OpenAPI-oriented notes.</p>
          </ContentCard>
        </>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Auth & session",
            body: "Register, verify email, login, MFA, password reset, and /auth/me for the signed-in operator profile.",
          },
          {
            title: "Devices",
            body: "Enrollment codes, agent download metadata, device inventory, and heartbeats from enrolled hosts.",
          },
          {
            title: "Detections",
            body: "Alerts, incidents, vulnerabilities/posture, and organization score endpoints for the dashboard.",
          },
          {
            title: "AI assist",
            body: "Server-side gateway endpoints for explanations and recommendations — no provider keys in the browser.",
          },
        ]}
      />
      <ContentCard title="Practical notes">
        <ul className="list-disc space-y-1 pl-4">
          <li>Prefer the customer web app for day-to-day operations; APIs power that UI.</li>
          <li>Treat demo-load endpoints as screenshot helpers, not production telemetry.</li>
          <li>
            Public product pages: <Link href="/platform">Platform</Link>, <Link href="/endpoint-security">Endpoint</Link>,{" "}
            <Link href="/security">Security</Link>.
          </li>
        </ul>
      </ContentCard>
    </Marketing>
  );
}
