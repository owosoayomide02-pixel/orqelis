import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Pricing"
      kicker="CONFIGURATION-DRIVEN"
      lead="Proposed starting plans for planning conversations. Production billing is not live in v0.1.0 — checkout uses a development provider only."
      aside={
        <>
          <ContentCard title="What you get">
            <ul className="list-disc space-y-1 pl-4">
              <li>Tenant dashboard</li>
              <li>Endpoint enrollment</li>
              <li>Detection + AI assist</li>
              <li>Human approval workflow</li>
            </ul>
          </ContentCard>
          <ContentCard title="Talk to us">
            <p>Need retention, SSO, or custom support commitments?</p>
            <Link href="/enterprise" className="mt-2 inline-block text-[var(--brand)]">
              Enterprise contact →
            </Link>
          </ContentCard>
        </>
      }
    >
      <div className="grid gap-3 md:grid-cols-3">
        {[
          {
            name: "Personal",
            price: "$20 / month",
            detail: "Individual operators protecting a small set of authorized endpoints.",
            points: ["Single organization", "Endpoint agent enrollment", "Alerts & basic reports"],
          },
          {
            name: "Business Core",
            price: "From $500 / month",
            detail: "Teams that need shared triage, posture tracking, and AI-assisted incident summaries.",
            points: ["Multi-user tenant", "Incidents & vulnerabilities", "AI security team views"],
          },
          {
            name: "Enterprise",
            price: "Contact sales",
            detail: "Negotiated terms, retention, support windows, and deployment constraints.",
            points: ["Custom agreements", "Founder-assisted onboarding", "No assumed certifications"],
          },
        ].map((plan) => (
          <div key={plan.name} className="glass rounded-2xl p-5">
            <div className="text-xs tracking-[0.2em] text-[var(--fg-muted)] uppercase">{plan.name}</div>
            <div className="mt-2 text-2xl font-semibold text-[var(--fg)]">{plan.price}</div>
            <p className="mt-2 text-sm leading-6">{plan.detail}</p>
            <ul className="mt-3 list-disc space-y-1 pl-4 text-sm">
              {plan.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <DetailGrid
        items={[
          {
            title: "Billing status",
            body: "Stripe/Paystack live charging is not enabled. Treat prices as planning figures until production billing ships.",
          },
          {
            title: "Refunds",
            body: "See the Refund Policy for draft terms. Final commercial terms may differ by contract.",
          },
        ]}
      />
      <div className="flex flex-wrap gap-3">
        <Link href="/register" className="btn btn-primary">
          Start free tenant
        </Link>
        <Link href="/docs/refund" className="btn btn-ghost">
          Refund policy
        </Link>
      </div>
    </Marketing>
  );
}
