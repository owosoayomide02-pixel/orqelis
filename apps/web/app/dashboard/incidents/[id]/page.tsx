"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, Severity } from "@/components/DashboardShell";
import { RunAI } from "@/components/SecurityWidgets";
import { api } from "@/lib/api";

type Incident = {
  id: string;
  title: string;
  summary: string;
  severity: string;
  status: string;
  risk_score: number;
  alert_ids: string[];
  event_ids: string[];
};

const STATUSES = ["open", "investigating", "contained", "resolved", "false_positive"];

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const [row, setRow] = useState<Incident | null>(null);
  async function load() {
    setRow(await api<Incident>(`/api/v1/incidents/${params.id}`));
  }
  useEffect(() => {
    load().catch(() => setRow(null));
  }, [params.id]);
  if (!row) return <EmptyState title="Incident" body="This incident is not in your organization." />;
  return (
    <div>
      <Link href="/dashboard/incidents" className="text-sm text-[var(--fg-muted)]">
        ← Incidents
      </Link>
      <div className="mt-4 flex items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold">{row.title}</h1>
        <Severity value={row.severity} />
      </div>
      <p className="mt-3 text-[var(--fg-muted)]">{row.summary}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        {STATUSES.map((status) => (
          <button
            key={status}
            className={`rounded-full border border-[var(--line)] px-3 py-1 text-sm ${row.status === status ? "text-[var(--ai)]" : "text-[var(--fg-muted)]"}`}
            onClick={async () => {
              const updated = await api<Incident>(`/api/v1/incidents/${row.id}/status`, {
                method: "POST",
                body: JSON.stringify({ status }),
              });
              setRow({ ...row, ...updated });
            }}
          >
            {status}
          </button>
        ))}
      </div>
      <h2 className="mt-8 text-xl">Linked alerts</h2>
      <div className="mt-3 space-y-2">
        {(row.alert_ids || []).map((id) => (
          <Link key={id} href={`/dashboard/alerts/${id}`} className="block text-sm text-[var(--ai)]">
            {id}
          </Link>
        ))}
      </div>
      <RunAI subjectType="incident" subjectId={row.id} />
    </div>
  );
}
