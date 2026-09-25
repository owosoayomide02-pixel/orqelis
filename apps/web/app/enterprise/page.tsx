import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Enterprise"
      kicker="CONTACT SALES"
      lead="Enterprise terms, retention, and support commitments are negotiated. Do not assume certifications such as ISO 27001 or SOC 2 until Orqelis has obtained them."
      aside={
        <>
          <ContentCard title="Sales contact">
            <p>Email: [SALES EMAIL]</p>
            <p className="mt-2">Include approximate endpoint count, operating systems, and whether you need a private deployment discussion.</p>
          </ContentCard>
          <ContentCard title="Also useful">
            <div className="flex flex-col gap-1.5">
              <Link href="/security">Security page →</Link>
              <Link href="/docs/dpa">Data Processing Addendum →</Link>
              <Link href="/company">Company / legal entity →</Link>
            </div>
          </ContentCard>
        </>
      }
    >
      <DetailGrid
        items={[
          {
            title: "What we discuss",
            body: "Seat/endpoint volume, retention windows, support expectations, identity integration needs, and contractual liability language.",
          },
          {
            title: "What we won’t claim",
            body: "ISO 27001, SOC 2, PCI DSS, or equivalent certifications are not represented as achieved in this release.",
          },
          {
            title: "Technical baseline",
            body: "Same V1 product: endpoint agents, rule-based detection, AI-assisted analysis, human approval for sensitive actions.",
          },
          {
            title: "Evaluation path",
            body: "Start with a tenant workspace, enroll authorized hosts, optionally load labeled demo data for stakeholder walkthroughs.",
          },
        ]}
      />
      <div className="flex flex-wrap gap-3">
        <Link href="/register" className="btn btn-primary">
          Open a trial tenant
        </Link>
        <Link href="/pricing" className="btn btn-ghost">
          See planning prices
        </Link>
      </div>
    </Marketing>
  );
}
