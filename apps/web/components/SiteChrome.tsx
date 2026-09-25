"use client";

import Link from "next/link";
import { useState } from "react";
import { publicNav } from "@/lib/nav";

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="mx-auto w-full max-w-6xl border-b border-[var(--line)] px-6 py-4">
      <div className="flex items-center justify-between">
        <Link href="/" className="tracking-[0.28em] text-xs text-[var(--fg-muted)]">
          ORQELIS
        </Link>
        <nav className="hidden items-center gap-5 text-sm text-[var(--fg-muted)] lg:flex">
          {publicNav.map((item) => (
            <Link key={item.href} href={item.href} className="hover:text-[var(--fg)]">
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm text-[var(--fg-muted)] hover:text-[var(--fg)]">
            Login
          </Link>
          <Link href="/register" className="btn btn-primary !py-2 !px-4 !text-xs">
            Get protected
          </Link>
          <button
            type="button"
            className="rounded-full border border-[var(--line)] px-3 py-2 text-xs uppercase tracking-wide text-[var(--fg-muted)] lg:hidden"
            aria-expanded={open}
            aria-controls="orqelis-mobile-nav"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? "Close" : "Menu"}
          </button>
        </div>
      </div>
      {open ? (
        <nav id="orqelis-mobile-nav" className="mt-3 flex flex-col gap-2 border-t border-[var(--line)] pt-3 text-sm text-[var(--fg-muted)] lg:hidden">
          {publicNav.map((item) => (
            <Link key={item.href} href={item.href} className="hover:text-[var(--fg)]" onClick={() => setOpen(false)}>
              {item.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mx-auto mt-12 w-full max-w-6xl border-t border-[var(--line)] px-6 py-8 text-sm text-[var(--fg-muted)]">
      <div className="grid gap-6 md:grid-cols-3">
        <div>
          <div className="text-xs tracking-[0.28em] text-[var(--fg)]">ORQELIS</div>
          <p className="mt-2 leading-6">AI-native endpoint security for Windows, macOS, and Linux. Detection stays rule-based; AI assists analysis and remediation guidance.</p>
        </div>
        <div>
          <div className="mb-2 text-xs uppercase tracking-[0.2em] text-[var(--fg)]">Product</div>
          <div className="flex flex-col gap-1.5">
            <Link href="/platform">Platform</Link>
            <Link href="/endpoint-security">Endpoint security</Link>
            <Link href="/ai-security">AI security</Link>
            <Link href="/pricing">Pricing</Link>
            <Link href="/enterprise">Enterprise</Link>
            <Link href="/developers">Developers</Link>
          </div>
        </div>
        <div>
          <div className="mb-2 text-xs uppercase tracking-[0.2em] text-[var(--fg)]">Legal & trust</div>
          <div className="flex flex-col gap-1.5">
            <Link href="/docs/privacy">Privacy Policy</Link>
            <Link href="/docs/terms">Terms of Service</Link>
            <Link href="/docs/cookies">Cookie Policy</Link>
            <Link href="/docs/aup">Acceptable Use</Link>
            <Link href="/security">Security</Link>
            <Link href="/docs/disclosure">Vulnerability Disclosure</Link>
            <Link href="/docs/dpa">DPA</Link>
            <Link href="/docs/refund">Refund Policy</Link>
            <Link href="/company">Contact</Link>
          </div>
        </div>
      </div>
      <p className="mt-6 border-t border-[var(--line)] pt-4">© 2026 Orqelis. All rights reserved. Early development release — not production-ready.</p>
    </footer>
  );
}

export function ContentCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass rounded-2xl p-5">
      <h2 className="text-base font-medium text-[var(--fg)]">{title}</h2>
      <div className="mt-2 space-y-2 text-sm leading-6 text-[var(--fg-muted)]">{children}</div>
    </div>
  );
}

export function DetailGrid({ items }: { items: { title: string; body: string }[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <ContentCard key={item.title} title={item.title}>
          <p>{item.body}</p>
        </ContentCard>
      ))}
    </div>
  );
}

export function Marketing({
  title,
  kicker,
  lead,
  aside,
  children,
}: {
  title: string;
  kicker?: string;
  lead?: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl px-6 py-8">
        <div className={aside ? "grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]" : ""}>
          <div>
            {kicker ? <div className="text-xs tracking-[0.28em] text-[var(--ai)]">{kicker}</div> : null}
            <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">{title}</h1>
            {lead ? <p className="mt-3 max-w-3xl text-base leading-7 text-[var(--fg-muted)]">{lead}</p> : null}
            <div className="mt-6 space-y-5 text-[var(--fg-muted)] leading-7">{children}</div>
          </div>
          {aside ? <aside className="space-y-3 lg:pt-10">{aside}</aside> : null}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}

export function AuthShell({
  title,
  kicker = "ORQELIS",
  children,
  panel,
}: {
  title: string;
  kicker?: string;
  children: React.ReactNode;
  panel: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl px-6 py-6">
        <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <aside className="order-2 space-y-3 lg:order-1">{panel}</aside>
          <div className="glass order-1 rounded-2xl p-5 md:p-6 lg:order-2">
            <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">{kicker}</div>
            <h1 className="mt-1.5 text-2xl font-semibold">{title}</h1>
            <div className="mt-4">{children}</div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}

export function AuthPanel({
  heading,
  points,
  next,
}: {
  heading: string;
  points: { title: string; body: string }[];
  next?: { title: string; body: string }[];
}) {
  return (
    <>
      <ContentCard title={heading}>
        <p>v0.1.0 focuses on endpoint protection with a dedicated detection engine and human-approved actions.</p>
      </ContentCard>
      <DetailGrid items={points} />
      {next?.length ? (
        <div className="glass rounded-2xl p-5">
          <h2 className="text-base font-medium text-[var(--fg)]">What happens next</h2>
          <ol className="mt-3 space-y-3 text-sm leading-6 text-[var(--fg-muted)]">
            {next.map((item, index) => (
              <li key={item.title} className="flex gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[var(--line)] text-xs text-[var(--fg)]">
                  {index + 1}
                </span>
                <span>
                  <span className="text-[var(--fg)]">{item.title}</span>
                  <br />
                  {item.body}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </>
  );
}
