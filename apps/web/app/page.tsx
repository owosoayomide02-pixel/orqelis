import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 pb-24 pt-20">
        <p className="text-xs tracking-[0.35em] text-[var(--ai)]">ORQELIS</p>
        <h1 className="mt-6 max-w-4xl text-5xl font-semibold leading-[1.05] tracking-tight md:text-7xl">
          SECURITY FOR THE
          <br />
          INTELLIGENT WORLD.
        </h1>
        <p className="mt-8 max-w-2xl text-lg text-[var(--fg-muted)]">
          Autonomous protection for humans, machines and artificial intelligence.
        </p>
        <div className="mt-10 flex flex-wrap gap-4">
          <Link href="/register" className="btn btn-primary">
            Get protected
          </Link>
          <Link href="/enterprise" className="btn btn-ghost">
            Enterprise
          </Link>
        </div>
        <div className="mt-20 grid gap-4 md:grid-cols-3">
          {[
            ["Endpoint security", "Enroll a Windows, macOS, or Linux agent, collect only security telemetry, and see devices come online."],
            ["Detection engine", "Rules and correlation identify suspicious behavior. An LLM is never the only detector."],
            ["Human approval", "AI explains and recommends. High-impact actions wait for an authorized person."],
          ].map(([title, body]) => (
            <div key={title} className="glass rounded-3xl p-6">
              <h2 className="text-lg">{title}</h2>
              <p className="mt-3 text-sm text-[var(--fg-muted)]">{body}</p>
            </div>
          ))}
        </div>
        <p className="mt-12 text-sm text-[var(--fg-muted)]">v0.1.0 is an early development release and is not production-ready.</p>
      </main>
      <SiteFooter />
    </div>
  );
}
