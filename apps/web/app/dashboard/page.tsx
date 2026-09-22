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
        <h1 className="text-3xl font-semibold">{org.name}</h1>
        <p className="mt-2 text-[var(--fg-muted)]">Role: {org.role}. A security score appears after an authorized agent enrolls.</p>
        <div className="mt-8 space-y-3">
          <EmptyState title="First-run checklist" body="1. Open Devices and create an enrollment code. 2. Install the Orqelis agent for Windows, macOS, or Linux on a computer you manage. 3. Run enroll, then run. Telemetry — not remote command execution — will populate this dashboard." />
          <div className="flex flex-wrap gap-3">
            <Link href="/dashboard/devices" className="btn btn-primary inline-flex">
              Enroll a device
            </Link>
            <button className="btn btn-ghost inline-flex" type="button" onClick={loadDemo}>
              Load labeled demo data
            </button>
          </div>
          <p className="text-sm text-[var(--fg-muted)]">Demo data is for screenshots only. It will not mix with a live enrolled agent.</p>
          {demoError ? <p className="text-sm text-[var(--critical)]">{demoError}</p> : null}
        </div>
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
      <h1 className="text-3xl font-semibold">{org.name}</h1>
      <p className="mt-2 text-[var(--fg-muted)]">{score.summary}</p>
      <div className="mt-8 grid gap-4 md:grid-cols-[280px_1fr]">
        <div className="glass rounded-3xl p-8 text-center">
          <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">ORQELIS SCORE</div>
          <div className="mt-4 text-7xl font-semibold" style={{ color: tone }}>
            {score.score}
          </div>
          <div className="mt-2 text-sm text-[var(--fg-muted)]">/ 100</div>
        </div>
        <div className="space-y-3">
          {score.drivers.length === 0 ? (
            <div className="glass rounded-3xl p-6 text-[var(--fg-muted)]">No score drivers. Keep the agent online and security controls enabled.</div>
          ) : (
            score.drivers.map((driver) => (
              <div key={driver.reason} className="glass rounded-3xl p-5">
                <div className="flex justify-between gap-4">
                  <div>{driver.reason}</div>
                  <div className="text-[var(--critical)]">{driver.impact}</div>
                </div>
                <p className="mt-2 text-sm text-[var(--fg-muted)]">{driver.fix}</p>
              </div>
            ))
          )}
        </div>
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={String(label)} className="glass rounded-3xl p-5">
            <div className="text-xs tracking-[0.2em] text-[var(--fg-muted)] uppercase">{label}</div>
            <div className="mt-3 text-3xl">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
