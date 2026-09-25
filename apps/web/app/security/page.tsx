import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Orqelis Security"
      kicker="SECURITY PAGE"
      lead="Orqelis is built with least privilege, role-based authorization, tenant isolation, encryption in transit, audit logging, secrets kept out of source control, and human approval for sensitive actions."
      aside={
        <>
          <ContentCard title="Report a vulnerability">
            <p>Email: [SECURITY EMAIL]</p>
            <Link href="/docs/disclosure" className="mt-2 inline-block text-[var(--brand)]">
              Disclosure policy →
            </Link>
          </ContentCard>
          <ContentCard title="Certifications">
            <p>Orqelis does not claim ISO 27001, SOC 2, or PCI DSS certification in this release.</p>
          </ContentCard>
        </>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Least privilege",
            body: "APIs and agent capabilities are scoped. High-impact actions require an authorized human approval path.",
          },
          {
            title: "Tenant isolation",
            body: "Customer data and telemetry are partitioned by organization. Sessions and device tokens are not interchangeable.",
          },
          {
            title: "Transport & secrets",
            body: "Encryption in transit for service traffic. Provider keys and secrets stay server-side and out of the repository.",
          },
          {
            title: "Auditability",
            body: "Sensitive operator actions and approvals are logged for accountability inside the tenant.",
          },
          {
            title: "Detection integrity",
            body: "Rules detect; AI explains. Generative models are not the sole security control.",
          },
          {
            title: "Agent boundaries",
            body: "The endpoint agent collects listed security telemetry only — no arbitrary remote command execution.",
          },
        ]}
      />
      <ContentCard title="Related resources">
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          <Link href="/docs/privacy">Privacy Policy</Link>
          <Link href="/docs/dpa">DPA</Link>
          <Link href="/docs/aup">Acceptable Use</Link>
          <Link href="/ai-security">AI security model</Link>
          <Link href="/endpoint-security">Endpoint agent</Link>
        </div>
      </ContentCard>
    </Marketing>
  );
}
