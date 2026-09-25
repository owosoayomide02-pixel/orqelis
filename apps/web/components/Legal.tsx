import Link from "next/link";
import type { ReactNode } from "react";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

function Legal({
  title,
  lead,
  children,
  aside,
}: {
  title: string;
  lead: string;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <Marketing title={title} kicker="LEGAL DRAFT" lead={lead} aside={aside}>
      <ContentCard title="Draft notice">
        <p>Effective Date: [DATE]. These documents are product-ready drafts, not a substitute for qualified legal review. Placeholders such as [LEGAL ENTITY NAME] must be replaced before production use.</p>
      </ContentCard>
      {children}
    </Marketing>
  );
}

export function PrivacyDoc() {
  return (
    <Legal
      title="Privacy Policy"
      lead="How Orqelis handles account data, security telemetry, and AI-assisted processing for customer tenants."
      aside={
        <ContentCard title="Contacts">
          <p>Legal entity: [LEGAL ENTITY NAME]</p>
          <p className="mt-2">Privacy: [PRIVACY EMAIL]</p>
          <Link href="/docs/dpa" className="mt-3 inline-block text-[var(--brand)]">
            Data Processing Addendum →
          </Link>
        </ContentCard>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Account information",
            body: "Name, organization, email, authentication secrets (hashed), MFA configuration, and marketing preference flags you set at registration.",
          },
          {
            title: "Security telemetry",
            body: "Listed endpoint signals from authorized agents — device, process, authentication, service, network metadata, and security-control status.",
          },
          {
            title: "AI processing",
            body: "Where configured, limited alert/incident context may be sent through the Orqelis AI gateway to a provider for explanations and recommendations.",
          },
          {
            title: "Audit records",
            body: "Operator actions and approvals retained to support accountability inside your tenant.",
          },
        ]}
      />
      <ContentCard title="Regional note">
        <p>Governing placeholders follow Nigerian data-protection considerations including NDPA 2023 until counsel finalizes the production policy.</p>
      </ContentCard>
    </Legal>
  );
}

export function TermsDoc() {
  return (
    <Legal
      title="Terms of Service"
      lead="By creating an account you agree to these Terms. You may only assess systems you own or are authorized to assess."
      aside={
        <ContentCard title="Contacts">
          <p>Jurisdiction: [JURISDICTION]</p>
          <p className="mt-2">Legal: [LEGAL EMAIL]</p>
          <Link href="/docs/aup" className="mt-3 inline-block text-[var(--brand)]">
            Acceptable Use →
          </Link>
        </ContentCard>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Accounts",
            body: "You are responsible for credential hygiene, MFA where enabled, and activity under your tenant users.",
          },
          {
            title: "Authorized use",
            body: "Endpoint agents and scanning features may only target systems you own or are explicitly authorized to manage.",
          },
          {
            title: "Service stage",
            body: "v0.1.0 is an early development release. Availability, billing, and packaging may change without production SLAs.",
          },
          {
            title: "Limitations",
            body: "Orqelis does not promise certifications, autonomous high-impact containment, or coverage outside the published V1 endpoint scope.",
          },
        ]}
      />
    </Legal>
  );
}
