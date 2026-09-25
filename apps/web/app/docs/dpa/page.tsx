import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Data Processing Agreement"
      kicker="TEMPLATE"
      lead="Where Orqelis processes customer security data on a customer’s instructions, the customer is generally the controller and Orqelis the processor. This template is not executed until reviewed."
      aside={
        <ContentCard title="Contacts">
          <p>Legal: [LEGAL EMAIL]</p>
          <p className="mt-2">Privacy: [PRIVACY EMAIL]</p>
          <Link href="/enterprise" className="mt-3 inline-block text-[var(--brand)]">
            Enterprise inquiry →
          </Link>
        </ContentCard>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Roles",
            body: "Customer typically acts as controller for tenant security data. Orqelis acts as processor when handling that data to provide the service.",
          },
          {
            title: "Categories of data",
            body: "Account identifiers, endpoint security telemetry, detection outcomes, audit logs, and limited AI-assist context where enabled.",
          },
          {
            title: "Instructions",
            body: "Processing follows product configuration and documented APIs — not open-ended secondary marketing use of telemetry.",
          },
          {
            title: "Subprocessors",
            body: "Infrastructure and optional AI providers may process data under Orqelis agreements. A production list will be maintained when live.",
          },
        ]}
      />
      <ContentCard title="Status">
        <p>This page is a contracting template for discussion. It is not an executed agreement until counsel reviews and parties sign.</p>
      </ContentCard>
    </Marketing>
  );
}
