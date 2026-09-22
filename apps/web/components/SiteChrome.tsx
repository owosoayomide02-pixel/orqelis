"use client";

import Link from "next/link";
import { useState } from "react";
import { publicNav } from "@/lib/nav";

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="mx-auto w-full max-w-6xl px-6 py-6">
      <div className="flex items-center justify-between">
        <Link href="/" className="tracking-[0.28em] text-xs text-[var(--fg-muted)]">
          ORQELIS
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-[var(--fg-muted)] md:flex">
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
            className="rounded-full border border-[var(--line)] px-3 py-2 text-xs uppercase tracking-wide text-[var(--fg-muted)] md:hidden"
            aria-expanded={open}
            aria-controls="orqelis-mobile-nav"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? "Close" : "Menu"}
          </button>
        </div>
      </div>
      {open ? (
        <nav id="orqelis-mobile-nav" className="mt-4 flex flex-col gap-3 border-t border-[var(--line)] pt-4 text-sm text-[var(--fg-muted)] md:hidden">
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
    <footer className="mx-auto mt-24 w-full max-w-6xl border-t border-[var(--line)] px-6 py-10 text-sm text-[var(--fg-muted)]">
      <div className="flex flex-wrap gap-x-6 gap-y-2">
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
      <p className="mt-6">© 2026 Orqelis. All rights reserved. Early development release — not production-ready.</p>
    </footer>
  );
}

export function Marketing({ title, kicker, children }: { title: string; kicker?: string; children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto w-full max-w-4xl px-6 py-16">
        {kicker ? <div className="text-xs tracking-[0.28em] text-[var(--ai)]">{kicker}</div> : null}
        <h1 className="mt-3 text-4xl font-semibold tracking-tight">{title}</h1>
        <div className="mt-8 space-y-4 text-[var(--fg-muted)] leading-7">{children}</div>
      </main>
      <SiteFooter />
    </div>
  );
}
