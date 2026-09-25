import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Company"
      kicker="ORQELIS"
      lead="Orqelis is an AI-native cybersecurity technology project. Legal entity name, registered address, and domain contacts remain placeholders until incorporation details are confirmed."
      aside={
        <>
          <ContentCard title="Entity placeholders">
            <p>Legal entity: [LEGAL ENTITY NAME]</p>
            <p className="mt-2">Address: [ADDRESS]</p>
          </ContentCard>
          <ContentCard title="Contact channels">
            <p>Privacy: [PRIVACY EMAIL]</p>
            <p>Security: [SECURITY EMAIL]</p>
            <p>Legal: [LEGAL EMAIL]</p>
            <p>Sales: [SALES EMAIL]</p>
          </ContentCard>
        </>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Product focus",
            body: "Version 1 ships endpoint security for Windows, macOS, and Linux with detection, AI assist, and human approval.",
          },
          {
            title: "Public site",
            body: "Marketing pages, pricing drafts, security disclosures, and legal documents live on this customer web app.",
          },
          {
            title: "Customer console",
            body: "Authenticated tenants manage devices, triage findings, and review reports after registration.",
          },
          {
            title: "Founder console",
            body: "A separate admin application supports internal operator workflows and is not part of the public navigation.",
          },
        ]}
      />
      <ContentCard title="Documents">
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          <Link href="/docs/privacy">Privacy</Link>
          <Link href="/docs/terms">Terms</Link>
          <Link href="/docs/cookies">Cookies</Link>
          <Link href="/docs/aup">Acceptable Use</Link>
          <Link href="/docs/dpa">DPA</Link>
          <Link href="/docs/refund">Refunds</Link>
          <Link href="/docs/disclosure">Vulnerability disclosure</Link>
        </div>
      </ContentCard>
    </Marketing>
  );
}
