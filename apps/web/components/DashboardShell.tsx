"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { nav } from "@/lib/nav";

type Me = {
  display_name: string;
  email_verified: boolean;
  dev_email_links?: boolean;
  organizations: { name: string }[];
};
type DemoStatus = { loaded: boolean; label: string };
type CriticalAlert = { id: string; title: string; severity: string };

const DISMISS_KEY = "orqelis_dismissed_critical";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [name, setName] = useState("Orqelis");
  const [verifyUrl, setVerifyUrl] = useState("");
  const [showVerify, setShowVerify] = useState(false);
  const [demoLabel, setDemoLabel] = useState("");
  const [critical, setCritical] = useState<CriticalAlert | null>(null);

  const loadCritical = useCallback(async () => {
    const rows = await api<CriticalAlert[]>("/api/v1/alerts?status=open&severity=critical&limit=1");
    const dismissed = typeof window !== "undefined" ? sessionStorage.getItem(DISMISS_KEY) : null;
    const next = rows[0] || null;
    setCritical(next && next.id !== dismissed ? next : null);
  }, []);

  useEffect(() => {
    api<Me>("/api/v1/auth/me")
      .then(async (me) => {
        setName(me.organizations?.[0]?.name || me.display_name);
        setShowVerify(Boolean(me.dev_email_links));
        const demo = await api<DemoStatus>("/api/v1/demo");
        setDemoLabel(demo.loaded ? demo.label : "");
        await loadCritical();
        setReady(true);
      })
      .catch(() => router.replace("/login"));
  }, [router, loadCritical]);

  useEffect(() => {
    if (!ready) return;
    const timer = window.setInterval(() => {
      loadCritical().catch(() => undefined);
    }, 20000);
    return () => window.clearInterval(timer);
  }, [ready, loadCritical]);

  if (!ready) {
    return <div className="flex min-h-screen items-center justify-center text-[var(--fg-muted)]">Loading Orqelis…</div>;
  }

  return (
    <div className="flex min-h-screen gap-6 p-5">
      <aside className="glass flex w-64 shrink-0 flex-col rounded-3xl p-5">
        <Link href="/dashboard" className="mb-8">
          <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">ORQELIS</div>
          <div className="mt-1 text-xl font-semibold">Security</div>
          <div className="mt-1 text-xs text-[var(--fg-muted)]">{name}</div>
        </Link>
        <nav className="flex flex-1 flex-col gap-1">
          {nav.map((item) => {
            const active = item.href === "/dashboard" ? pathname === "/dashboard" : pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-2xl px-3 py-2.5 text-sm ${active ? "bg-[rgba(124,92,255,0.16)] text-[var(--brand)]" : "text-[var(--fg-muted)] hover:text-[var(--fg)]"}`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <button
          className="mt-4 text-left text-sm text-[var(--fg-muted)]"
          onClick={async () => {
            await api("/api/v1/auth/logout", { method: "POST" });
            router.replace("/login");
          }}
        >
          Sign out
        </button>
      </aside>
      <main className="min-w-0 flex-1 py-4 pr-2">
        <div className="mb-4 space-y-3">
          {showVerify ? (
            <div className="glass rounded-3xl border border-[var(--warning)] p-4">
              <div className="text-sm font-medium">Verify your email</div>
              <p className="mt-1 text-sm text-[var(--fg-muted)]">SMTP is unset in this development environment. The verification link is also printed in the API log.</p>
              {verifyUrl ? (
                <p className="mt-2 break-all text-sm">
                  <a href={verifyUrl} className="text-[var(--brand)]">
                    {verifyUrl}
                  </a>
                </p>
              ) : (
                <button
                  className="btn btn-primary mt-3 !py-2"
                  onClick={async () => {
                    const result = await api<{ verification_url?: string }>("/api/v1/auth/verification-link", { method: "POST" });
                    setVerifyUrl(result.verification_url || "");
                  }}
                >
                  Show verification link
                </button>
              )}
            </div>
          ) : null}
          {demoLabel ? (
            <div className="glass rounded-3xl border border-[var(--ai)] p-4 text-sm">
              <span className="font-medium">{demoLabel}.</span> This workspace is for screenshots. It is not live telemetry.
            </div>
          ) : null}
          {critical ? (
            <div className="glass flex items-start justify-between gap-4 rounded-3xl border border-[var(--critical)] p-4">
              <div>
                <div className="text-xs tracking-[0.2em] text-[var(--critical)]">CRITICAL ALERT</div>
                <div className="mt-1">{critical.title}</div>
                <Link href={`/dashboard/alerts/${critical.id}`} className="mt-2 inline-block text-sm text-[var(--brand)]">
                  Open alert
                </Link>
              </div>
              <button
                className="text-sm text-[var(--fg-muted)]"
                onClick={() => {
                  sessionStorage.setItem(DISMISS_KEY, critical.id);
                  setCritical(null);
                }}
              >
                Dismiss
              </button>
            </div>
          ) : null}
        </div>
        {children}
      </main>
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="glass rounded-3xl p-8 text-[var(--fg-muted)]">
      <div className="text-lg text-[var(--fg)]">{title}</div>
      <p className="mt-2 max-w-2xl">{body}</p>
    </div>
  );
}

export function Severity({ value }: { value: string }) {
  return (
    <span className="rounded-full border border-[var(--line)] px-2 py-1 text-xs uppercase tracking-wide" style={{ color: `var(--${value === "critical" ? "critical" : value === "high" ? "high" : value === "medium" ? "warning" : "ai"})` }}>
      {value}
    </span>
  );
}
