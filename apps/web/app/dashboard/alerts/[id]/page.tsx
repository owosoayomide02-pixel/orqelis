"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, Severity } from "@/components/DashboardShell";
import { RunAI } from "@/components/SecurityWidgets";
import { api } from "@/lib/api";

type Alert = {
  id: string;
  device_id: string | null;
  title: string;
  severity: string;
  confidence: number;
  risk_score: number;
  rule_id: string;
  evidence: unknown;
  recommended_next_step: string;
  status: string;
  created_at: string;
};

type Analysis = { id: string; role: string; provider: string; output: { explanation?: string } };

export default function AlertDetailPage() {
  const params = useParams<{ id: string }>();
  const [row, setRow] = useState<Alert | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  useEffect(() => {
    Promise.all([
      api<Alert>(`/api/v1/alerts/${params.id}`),
      api<Analysis[]>(`/api/v1/ai/analyses?subject_id=${params.id}`),
    ])
      .then(([alertRow, analysisRows]) => {
        setRow(alertRow);
        setAnalyses(analysisRows);
      })
      .catch(() => setRow(null));
  }, [params.id]);
  if (!row) return <EmptyState title="Alert" body="This alert is not in your organization." />;
  return (
    <div>
      <Link href="/dashboard/alerts" className="text-sm text-[var(--fg-muted)]">
        ← Alerts
      </Link>
      <div className="mt-4 flex items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold">{row.title}</h1>
        <Severity value={row.severity} />
      </div>
      <p className="mt-2 text-sm text-[var(--fg-muted)]">
        {row.rule_id} · risk {row.risk_score} · confidence {Math.round(row.confidence * 100)}% · {row.status}
      </p>
      <p className="mt-6">{row.recommended_next_step}</p>
      {row.device_id ? (
        <Link href={`/dashboard/devices/${row.device_id}`} className="mt-4 inline-block text-sm text-[var(--ai)]">
          View device
        </Link>
      ) : null}
      {analyses.length ? (
        <div className="mt-6 space-y-3">
          {analyses.map((item) => (
            <div key={item.id} className="glass rounded-3xl p-5">
              <div className="text-xs uppercase tracking-wide text-[var(--ai)]">
                {item.role} · {item.provider}
              </div>
              <p className="mt-2 text-sm text-[var(--fg-muted)]">{item.output?.explanation}</p>
            </div>
          ))}
        </div>
      ) : null}
      <pre className="glass mt-6 overflow-x-auto rounded-3xl p-5 text-xs text-[var(--fg-muted)]">{JSON.stringify(row.evidence, null, 2)}</pre>
      <RunAI subjectType="alert" subjectId={row.id} />
    </div>
  );
}
