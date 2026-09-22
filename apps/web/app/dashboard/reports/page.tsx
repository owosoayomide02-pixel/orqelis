"use client";

import { useEffect, useState } from "react";
import { EmptyState } from "@/components/DashboardShell";
import { api } from "@/lib/api";

type Report = { id: string; title: string; body_markdown: string };

export default function ReportsPage() {
  const [rows, setRows] = useState<Report[]>([]);
  async function load() {
    setRows(await api<Report[]>("/api/v1/reports"));
  }
  useEffect(() => {
    load().catch(() => setRows([]));
  }, []);
  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold">Reports</h1>
        <button
          className="btn btn-primary"
          onClick={async () => {
            await api("/api/v1/reports", { method: "POST" });
            await load();
          }}
        >
          Generate report
        </button>
      </div>
      <div className="mt-8 space-y-3">
        {rows.length === 0 ? (
          <EmptyState title="No reports" body="Generate a report from actual tenant counts and detections." />
        ) : (
          rows.map((row) => (
            <div key={row.id} className="glass rounded-3xl p-5">
              <div className="text-lg">{row.title}</div>
              <pre className="mt-3 whitespace-pre-wrap text-sm text-[var(--fg-muted)]">{row.body_markdown}</pre>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
