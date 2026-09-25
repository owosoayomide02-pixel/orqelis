import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Platform"
      kicker="ORQELIS V1"
      lead="Orqelis is an AI-native cybersecurity platform. Version 1 concentrates on endpoint security, a dedicated detection engine, AI-assisted analysis, a customer dashboard, and a private founder console."
      aside={
        <>
          <ContentCard title="In scope now">
            <ul className="list-disc space-y-1 pl-4">
              <li>Windows / macOS / Linux agents</li>
              <li>Rule-based detection + correlation</li>
              <li>AI explanations & recommendations</li>
              <li>Human-approved actions</li>
              <li>Tenant dashboard + reports</li>
            </ul>
          </ContentCard>
          <ContentCard title="Not live in V1">
            <ul className="list-disc space-y-1 pl-4">
              <li>Web / API / cloud / code products</li>
              <li>Security graph / attack paths</li>
              <li>Autonomous isolate or kill-process</li>
              <li>Marketplace</li>
            </ul>
          </ContentCard>
          <ContentCard title="Next reads">
            <div className="flex flex-col gap-1.5">
              <Link href="/endpoint-security">Endpoint security →</Link>
              <Link href="/ai-security">AI security →</Link>
              <Link href="/security">Trust & security →</Link>
              <Link href="/developers">Developer APIs →</Link>
            </div>
          </ContentCard>
        </>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Agent → API → detection",
            body: "Authorized agents stream listed security telemetry to the Orqelis API. The detection package evaluates rules without requiring an LLM round-trip.",
          },
          {
            title: "AI gateway",
            body: "Explanations and remediation drafts run through an internal gateway so provider keys never reach browsers or endpoints.",
          },
          {
            title: "Customer console",
            body: "Operators enroll devices, triage alerts and incidents, review posture findings, and manage subscription settings per tenant.",
          },
          {
            title: "Extension points",
            body: "Later domains — web, API, cloud, code, mobile, network, identity — share the same tenancy and approval model but are not presented as live products yet.",
          },
        ]}
      />
      <ContentCard title="Operating model">
        <p>
          Detection stays deterministic. AI assists understanding. High-impact changes wait for a person. That separation is
          intentional so an LLM hallucination cannot be the sole path to a protective action.
        </p>
      </ContentCard>
    </Marketing>
  );
}
