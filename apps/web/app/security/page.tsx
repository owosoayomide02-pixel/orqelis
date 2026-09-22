import { Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing title="Orqelis Security" kicker="SECURITY PAGE">
      <p>
        Orqelis is built with least privilege, role-based authorization, tenant isolation, encryption in transit, audit
        logging, secrets kept out of source control, and human approval for sensitive actions.
      </p>
      <p>Orqelis does not claim ISO 27001, SOC 2, or PCI DSS certification in this release.</p>
      <p>Report vulnerabilities to [SECURITY EMAIL].</p>
    </Marketing>
  );
}
