import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

const docs = [
  { href: "/docs/privacy", title: "Privacy Policy", body: "What Orqelis processes and how to reach privacy contacts." },
  { href: "/docs/terms", title: "Terms of Service", body: "Account use, authorization boundaries, and jurisdiction placeholders." },
  { href: "/docs/cookies", title: "Cookie Policy", body: "Session and preference cookies used by the customer web app." },
  { href: "/docs/aup", title: "Acceptable Use", body: "Authorized systems only — no unauthorized scanning or abuse." },
  { href: "/docs/dpa", title: "DPA", body: "Draft data processing terms for enterprise contracting conversations." },
  { href: "/docs/refund", title: "Refund Policy", body: "Draft commercial refund language while billing remains non-production." },
  { href: "/docs/disclosure", title: "Vulnerability Disclosure", body: "How to report security issues to [SECURITY EMAIL]." },
  { href: "/security", title: "Security page", body: "Product security practices and explicit non-claims." },
];

export default function Page() {
  return (
    <Marketing
      title="Documentation"
      kicker="PUBLIC"
      lead="Public legal drafts and trust pages for the Orqelis customer site. Full product and engineering guides also live in the repository docs directory."
      aside={
        <>
          <ContentCard title="Quick links">
            <div className="flex flex-col gap-1.5">
              <Link href="/platform">Platform overview →</Link>
              <Link href="/endpoint-security">Endpoint agent →</Link>
              <Link href="/ai-security">AI security →</Link>
              <Link href="/developers">API notes →</Link>
              <Link href="/register">Create account →</Link>
            </div>
          </ContentCard>
          <ContentCard title="Status">
            <p>Legal documents are product-ready drafts with placeholders such as [LEGAL ENTITY NAME]. They are not a substitute for qualified legal review.</p>
          </ContentCard>
        </>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {docs.map((doc) => (
          <Link key={doc.href} href={doc.href} className="glass rounded-2xl p-5 transition hover:border-[var(--brand)]">
            <div className="text-base font-medium text-[var(--fg)]">{doc.title}</div>
            <p className="mt-2 text-sm leading-6 text-[var(--fg-muted)]">{doc.body}</p>
          </Link>
        ))}
      </div>
      <DetailGrid
        items={[
          {
            title: "Customer journey",
            body: "Register → verify email → enroll agent → triage alerts/incidents → review reports and subscription.",
          },
          {
            title: "Engineering docs",
            body: "Architecture, runbooks, and API detail remain in the monorepo docs/ tree for contributors and operators.",
          },
        ]}
      />
    </Marketing>
  );
}
