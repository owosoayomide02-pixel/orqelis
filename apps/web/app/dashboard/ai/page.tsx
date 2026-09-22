"use client";

import { useEffect, useState } from "react";
import { EmptyState } from "@/components/DashboardShell";
import { api } from "@/lib/api";

const ROLES = [
  { id: "sentinel", title: "Sentinel", body: "Triage alerts and say what needs investigation." },
  { id: "hunter", title: "Hunter", body: "Search authorized telemetry for suspicious patterns." },
  { id: "analyst", title: "Analyst", body: "Investigate incidents and produce a timeline." },
  { id: "auditor", title: "Auditor", body: "Review device posture and configuration." },
  { id: "fixer", title: "Fixer", body: "Recommend defensive remediation only." },
];

type Alert = { id: string; title: string };
type Analysis = { id: string; role: string; provider: string; output: { explanation?: string }; created_at: string };

export default function AIPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [role, setRole] = useState("analyst");
  const [alertId, setAlertId] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [a, b] = await Promise.all([api<Alert[]>("/api/v1/alerts"), api<Analysis[]>("/api/v1/ai/analyses")]);
    setAlerts(a);
    setAnalyses(b);
    if (!alertId && a[0]) setAlertId(a[0].id);
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function run() {
    setError("");
    try {
      await api("/api/v1/ai/analyze", {
        method: "POST",
        body: JSON.stringify({ role, subject_type: "alert", subject_id: alertId }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-semibold">AI Security Team</h1>
      <p className="mt-2 text-[var(--fg-muted)]">
        Five workflows, one model gateway. Analysis uses redacted tenant data. High-impact actions still require approval.
      </p>
      <div className="mt-8 grid gap-3 md:grid-cols-5">
        {ROLES.map((item) => (
          <button
            key={item.id}
            onClick={() => setRole(item.id)}
            className={`glass rounded-3xl p-4 text-left ${role === item.id ? "ring-1 ring-[var(--ai)]" : ""}`}
          >
            <div>{item.title}</div>
            <p className="mt-2 text-xs text-[var(--fg-muted)]">{item.body}</p>
          </button>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <select className="max-w-md" value={alertId} onChange={(e) => setAlertId(e.target.value)}>
          {alerts.map((alert) => (
            <option key={alert.id} value={alert.id}>
              {alert.title}
            </option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={run} disabled={!alertId}>
          Run {role}
        </button>
      </div>
      {error ? <p className="mt-3 text-[var(--critical)]">{error}</p> : null}
      <div className="mt-8 space-y-3">
        {analyses.length === 0 ? (
          <EmptyState title="No analyses yet" body="Run a role against a real alert. Heuristic mode is used when no AI key is configured." />
        ) : (
          analyses.map((item) => (
            <div key={item.id} className="glass rounded-3xl p-5">
              <div className="text-sm uppercase tracking-wide text-[var(--ai)]">
                {item.role} · {item.provider}
              </div>
              <p className="mt-3 text-sm text-[var(--fg-muted)]">{item.output?.explanation}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
