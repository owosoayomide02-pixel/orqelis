"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, Severity } from "@/components/DashboardShell";
import { api } from "@/lib/api";

type Alert = {
  id: string;
  title: string;
  severity: string;
  risk_score: number;
  confidence: number;
  recommended_next_step: string;
  created_at: string;
};

export default function AlertsPage() {
  const [rows, setRows] = useState<Alert[]>([]);
  useEffect(() => {
    api<Alert[]>("/api/v1/alerts").then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div>
      <h1 className="text-3xl font-semibold">Alerts</h1>
      <p className="mt-2 text-[var(--fg-muted)]">Produced by the detection engine, not by an LLM.</p>
      <div className="mt-8 space-y-3">
        {rows.length === 0 ? (
          <EmptyState title="No alerts" body="Alerts appear after enrolled devices send telemetry that matches a detection rule." />
        ) : (
          rows.map((row) => (
            <Link key={row.id} href={`/dashboard/alerts/${row.id}`} className="glass block rounded-3xl p-5">
              <div className="flex items-center justify-between gap-4">
                <div className="text-lg">{row.title}</div>
                <Severity value={row.severity} />
              </div>
              <div className="mt-2 text-sm text-[var(--fg-muted)]">
                Risk {row.risk_score} · confidence {Math.round(row.confidence * 100)}%
              </div>
              <p className="mt-3 text-sm">{row.recommended_next_step}</p>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
