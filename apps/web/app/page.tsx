import Link from "next/link";
import { ContentCard, DetailGrid, SiteFooter, SiteHeader } from "@/components/SiteChrome";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 pb-12 pt-10">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:items-end">
          <div>
            <p className="text-xs tracking-[0.35em] text-[var(--ai)]">ORQELIS · v0.1.0</p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.08] tracking-tight md:text-6xl">
              SECURITY FOR THE
              <br />
              INTELLIGENT WORLD.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[var(--fg-muted)] md:text-lg">
              Autonomous protection for humans, machines and artificial intelligence — starting with Windows, macOS, and
              Linux endpoint security you can enroll, monitor, and approve.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/register" className="btn btn-primary">
                Get protected
              </Link>
              <Link href="/login?next=/dashboard/devices" className="btn btn-ghost">
                Download for Windows
              </Link>
              <Link href="/platform" className="btn btn-ghost">
                Explore platform
              </Link>
              <Link href="/enterprise" className="btn btn-ghost">
                Enterprise
              </Link>
            </div>
          </div>
          <div className="glass rounded-2xl p-5">
            <div className="text-xs tracking-[0.24em] text-[var(--fg-muted)]">FIRST 15 MINUTES</div>
            <ol className="mt-3 space-y-3 text-sm leading-6 text-[var(--fg-muted)]">
              <li>
                <span className="text-[var(--fg)]">1. Create a tenant</span> — register organization + verify email.
              </li>
              <li>
                <span className="text-[var(--fg)]">2. Enroll an endpoint</span> — install the Orqelis agent on a machine you manage.
              </li>
              <li>
                <span className="text-[var(--fg)]">3. Review detections</span> — alerts, incidents, posture, and AI explanations appear in the dashboard.
              </li>
            </ol>
            <Link href="/endpoint-security" className="mt-4 inline-block text-sm text-[var(--brand)]">
              How the agent works →
            </Link>
          </div>
        </div>

        <section className="mt-10">
          <div className="mb-3 flex items-end justify-between gap-4">
            <h2 className="text-xl font-semibold">What ships in Version 1</h2>
            <Link href="/platform" className="text-sm text-[var(--fg-muted)] hover:text-[var(--fg)]">
              Full platform map
            </Link>
          </div>
          <DetailGrid
            items={[
              {
                title: "Endpoint security",
                body: "Enroll Windows, macOS, or Linux agents. Collect listed security telemetry only — not remote shells or personal file browsing.",
              },
              {
                title: "Detection engine",
                body: "Deterministic rules and correlation identify suspicious behavior. An LLM is never the only detector.",
              },
              {
                title: "AI-assisted analysis",
                body: "An internal AI gateway explains alerts, summarizes incidents, and recommends remediation without exposing provider keys to browsers or agents.",
              },
              {
                title: "Human approval",
                body: "AI recommends; authorized operators approve a small set of supported agent actions before they run.",
              },
              {
                title: "Customer dashboard",
                body: "Devices, alerts, incidents, vulnerabilities, reports, subscription, and settings in one tenant console.",
              },
              {
                title: "Founder admin",
                body: "A private admin console supports operator oversight. It is separate from the customer web app.",
              },
            ]}
          />
        </section>

        <section className="mt-10 grid gap-3 md:grid-cols-3">
          <ContentCard title="Designed boundaries">
            <p>Web, API, cloud, code, mobile, network, and identity products are architectural extension points — not live V1 offerings.</p>
          </ContentCard>
          <ContentCard title="Trust posture">
            <p>Least privilege, tenant isolation, encryption in transit, audit logging, and no ISO/SOC 2 claims until earned.</p>
          </ContentCard>
          <ContentCard title="Early release">
            <p>v0.1.0 is early development. Billing providers, signed installers, and production hardening are still in progress.</p>
          </ContentCard>
        </section>

        <section className="mt-10 grid gap-4 rounded-2xl border border-[var(--line)] p-5 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <h2 className="text-lg font-semibold">Start with a tenant workspace</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--fg-muted)]">
              Create an account, enroll your first authorized endpoint, and explore detections with live or labeled demo data.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/register" className="btn btn-primary">
              Create account
            </Link>
            <Link href="/pricing" className="btn btn-ghost">
              View pricing
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
