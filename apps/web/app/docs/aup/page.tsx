import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Acceptable Use Policy"
      kicker="LEGAL DRAFT"
      lead="You may not use Orqelis for unauthorized testing, malware, fraud, or attacks against systems you do not own or have written authorization to assess."
      aside={
        <ContentCard title="Report abuse">
          <p>Security: [SECURITY EMAIL]</p>
          <Link href="/docs/disclosure" className="mt-2 inline-block text-[var(--brand)]">
            Vulnerability disclosure →
          </Link>
        </ContentCard>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Authorized targets only",
            body: "Enroll agents and assess only computers and networks you own or are explicitly authorized to manage.",
          },
          {
            title: "No offensive misuse",
            body: "Do not use Orqelis to distribute malware, run unauthorized intrusion campaigns, commit fraud, or disrupt third-party services.",
          },
          {
            title: "Credential hygiene",
            body: "Do not share tenant credentials, exfiltrate other customers’ data, or attempt to bypass access controls.",
          },
          {
            title: "Fair use of AI assist",
            body: "Do not attempt to coerce the AI gateway into generating attack tooling or circumventing product safety boundaries.",
          },
        ]}
      />
      <ContentCard title="Enforcement">
        <p>Orqelis may suspend accounts that violate this policy. Serious abuse may be reported to appropriate authorities where required.</p>
      </ContentCard>
    </Marketing>
  );
}
