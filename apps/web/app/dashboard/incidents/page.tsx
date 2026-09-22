"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, Severity } from "@/components/DashboardShell";
import { api } from "@/lib/api";

type Incident = { id: string; title: string; summary: string; severity: string; status: string; risk_score: number };

export default function IncidentsPage() {
  const [rows, setRows] = useState<Incident[]>([]);
  useEffect(() => {
    api<Incident[]>("/api/v1/incidents").then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div>
      <h1 className="text-3xl font-semibold">Incidents</h1>
      <p className="mt-2 text-[var(--fg-muted)]">Related detections are correlated instead of firing as isolated noise.</p>
      <div className="mt-8 space-y-3">
        {rows.length === 0 ? (
          <EmptyState title="No incidents" body="Incidents are created when detections on the same device correlate." />
        ) : (
          rows.map((row) => (
            <Link key={row.id} href={`/dashboard/incidents/${row.id}`} className="glass block rounded-3xl p-5">
              <div className="flex items-center justify-between">
                <div className="text-lg">{row.title}</div>
                <Severity value={row.severity} />
              </div>
              <p className="mt-2 text-sm text-[var(--fg-muted)]">{row.summary}</p>
              <div className="mt-3 text-xs uppercase tracking-wide text-[var(--fg-muted)]">
                {row.status} · risk {row.risk_score}
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
