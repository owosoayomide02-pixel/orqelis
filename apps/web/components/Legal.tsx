import { Marketing } from "@/components/SiteChrome";

function Legal({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Marketing title={title} kicker="LEGAL DRAFT">
      <p>Effective Date: [DATE]. These documents are product-ready drafts, not a substitute for qualified legal review.</p>
      {children}
    </Marketing>
  );
}

export function PrivacyDoc() {
  return (
    <Legal title="Privacy Policy">
      <p>
        Orqelis processes account information, security telemetry from authorized endpoint agents, audit records, and (where
        configured) limited data sent to an AI provider through the Orqelis AI gateway.
      </p>
      <p>Legal entity: [LEGAL ENTITY NAME]. Privacy: [PRIVACY EMAIL]. Governing placeholders follow Nigerian data-protection considerations including NDPA 2023.</p>
    </Legal>
  );
}

export function TermsDoc() {
  return (
    <Legal title="Terms of Service">
      <p>By creating an account you agree to these Terms. You may only assess systems you own or are authorized to assess.</p>
      <p>Jurisdiction: [JURISDICTION]. Legal: [LEGAL EMAIL].</p>
    </Legal>
  );
}
