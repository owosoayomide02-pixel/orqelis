import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Vulnerability Disclosure"
      kicker="SECURITY"
      lead="Report issues affecting Orqelis systems to [SECURITY EMAIL]. Avoid accessing unnecessary data, destructive testing, or service disruption."
      aside={
        <ContentCard title="Preferred channel">
          <p>[SECURITY EMAIL]</p>
          <Link href="/security" className="mt-3 inline-block text-[var(--brand)]">
            Security practices →
          </Link>
        </ContentCard>
      }
    >
      <DetailGrid
        items={[
          {
            title: "In scope",
            body: "Customer web app, API, agent enrollment flows, authentication, tenant isolation flaws, and injection issues in Orqelis-operated services.",
          },
          {
            title: "Out of scope",
            body: "Social engineering of staff, physical attacks, DoS that disrupts availability, and testing against other customers’ tenants.",
          },
          {
            title: "Safe harbor expectations",
            body: "Act in good faith, minimize data access, do not exploit beyond proof, and give Orqelis reasonable time to remediate before public detail.",
          },
          {
            title: "What to include",
            body: "Affected URL/endpoint, reproduction steps, impact assessment, and your contact details for follow-up.",
          },
        ]}
      />
      <ContentCard title="Thanks">
        <p>Responsible reports help keep Orqelis tenants safer. We will acknowledge receipt when the security mailbox is staffed for production.</p>
      </ContentCard>
    </Marketing>
  );
}
