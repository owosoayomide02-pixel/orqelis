import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Endpoint Security"
      kicker="WINDOWS · MACOS · LINUX"
      lead="The Orqelis agent collects device, process, authentication, service, network metadata, and security-control status. It does not execute arbitrary remote commands and does not read personal files."
      aside={
        <>
          <ContentCard title="Install only where authorized">
            <p>Use the agent on computers you own or are explicitly authorized to manage. Unauthorized assessment is out of scope and against the Acceptable Use Policy.</p>
          </ContentCard>
          <ContentCard title="Enrollment path">
            <ol className="list-decimal space-y-1 pl-4">
              <li>Open Devices in the dashboard</li>
              <li>Create an enrollment code</li>
              <li>Install the platform package</li>
              <li>Run enroll, then run</li>
            </ol>
            <Link href="/register" className="mt-3 inline-block text-[var(--brand)]">
              Create a tenant →
            </Link>
          </ContentCard>
        </>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Windows",
            body: "Security log and Defender-oriented control status, plus process and host metadata collectors appropriate to the platform.",
          },
          {
            title: "macOS",
            body: "Gatekeeper and application firewall signals alongside shared host, process, and network metadata collection.",
          },
          {
            title: "Linux",
            body: "Auth logs and host firewall posture, with the same telemetry categories the detection engine already understands.",
          },
          {
            title: "Hard boundaries",
            body: "No remote shell, no general remote control, no arbitrary command execution. Supported actions are narrow and human-approved.",
          },
        ]}
      />
      <ContentCard title="What the dashboard shows after enrollment">
        <p>
          Online devices, last-seen heartbeats, open alerts, correlated incidents, posture findings, and an Orqelis score
          driven by measurable control gaps — not marketing placeholders.
        </p>
      </ContentCard>
    </Marketing>
  );
}
