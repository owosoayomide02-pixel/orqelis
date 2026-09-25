"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/DashboardShell";
import { api } from "@/lib/api";

type Org = {
  name: string;
  role: string;
  demo?: boolean;
  demo_label?: string | null;
  counts: { devices: number; alerts: number; incidents: number; vulnerabilities: number };
};
type Score = {
  score: number | null;
  first_run: boolean;
  summary: string;
  drivers: { reason: string; impact: number; fix: string }[];
  counts: { devices: number; alerts_open: number; incidents_open: number; vulnerabilities_open: number };
};

export default function OverviewPage() {
  const [org, setOrg] = useState<Org | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [demoError, setDemoError] = useState("");

  async function load() {
    const [orgRow, scoreRow] = await Promise.all([
      api<Org>("/api/v1/organizations/current"),
      api<Score>("/api/v1/organizations/current/score"),
    ]);
    setOrg(orgRow);
    setScore(scoreRow);
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function loadDemo() {
    setDemoError("");
    try {
      await api("/api/v1/demo/load", { method: "POST" });
      window.location.reload();
    } catch (err) {
      setDemoError(err instanceof Error ? err.message : "Could not load demo data");
    }
  }
  if (!org || !score) return <EmptyState title="Overview" body="Sign in to load tenant data." />;

  if (score.first_run) {
    return (
      <div>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold md:text-3xl">{org.name}</h1>
            <p className="mt-1 text-sm text-[var(--fg-muted)]">Role: {org.role}. A security score appears after an authorized agent enrolls.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/dashboard/devices" className="btn btn-primary inline-flex !py-2">
              Enroll a device
            </Link>
            <button className="btn btn-ghost inline-flex !py-2" type="button" onClick={loadDemo}>
              Load labeled demo data
            </button>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {[
            ["1. Enrollment code", "Open Devices and create an enrollment code for an authorized host."],
            ["2. Install agent", "Install the Orqelis agent for Windows, macOS, or Linux on a computer you manage."],
            ["3. Run enroll", "Run enroll, then run. Telemetry — not remote command execution — populates this dashboard."],
          ].map(([title, body]) => (
            <div key={title} className="glass rounded-2xl p-4">
              <div className="text-sm font-medium">{title}</div>
              <p className="mt-2 text-sm leading-6 text-[var(--fg-muted)]">{body}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <EmptyState title="What will appear here" body="Orqelis score, open alerts, correlated incidents, posture findings, and device heartbeats once an agent is online. Demo data is for screenshots only and will not mix with a live enrolled agent." />
          <EmptyState title="Safe operating boundary" body="The agent collects listed security telemetry only. It does not provide a remote shell or arbitrary command execution. High-impact actions require human approval." />
        </div>
        {demoError ? <p className="mt-3 text-sm text-[var(--critical)]">{demoError}</p> : null}
      </div>
    );
  }

  const tone = (score.score ?? 0) >= 80 ? "var(--success)" : (score.score ?? 0) >= 50 ? "var(--warning)" : "var(--critical)";
  const cards = [
    ["Devices", score.counts.devices],
    ["Open alerts", score.counts.alerts_open],
    ["Open incidents", score.counts.incidents_open],
    ["Posture findings", score.counts.vulnerabilities_open],
  ];
  return (
    <div>
      <h1 className="text-2xl font-semibold md:text-3xl">{org.name}</h1>
      <p className="mt-1 text-sm text-[var(--fg-muted)]">{score.summary}</p>
      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={String(label)} className="glass rounded-2xl p-4">
            <div className="text-xs tracking-[0.2em] text-[var(--fg-muted)] uppercase">{label}</div>
            <div className="mt-2 text-3xl">{value}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-[240px_1fr]">
        <div className="glass rounded-2xl p-5 text-center">
          <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">ORQELIS SCORE</div>
          <div className="mt-3 text-6xl font-semibold" style={{ color: tone }}>
            {score.score}
          </div>
          <div className="mt-1 text-sm text-[var(--fg-muted)]">/ 100</div>
        </div>
        <div className="space-y-2">
          {score.drivers.length === 0 ? (
            <div className="glass rounded-2xl p-4 text-sm text-[var(--fg-muted)]">No score drivers. Keep the agent online and security controls enabled.</div>
          ) : (
            score.drivers.map((driver) => (
              <div key={driver.reason} className="glass rounded-2xl p-4">
                <div className="flex justify-between gap-4">
                  <div className="text-sm">{driver.reason}</div>
                  <div className="text-sm text-[var(--critical)]">{driver.impact}</div>
                </div>
                <p className="mt-1.5 text-sm text-[var(--fg-muted)]">{driver.fix}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
