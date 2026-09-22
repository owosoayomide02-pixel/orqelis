"use client";

import { useEffect, useState } from "react";
import { EmptyState, Severity } from "@/components/DashboardShell";
import { api } from "@/lib/api";

type Item = { id: string; title: string; description: string; severity: string; source: string };

export default function Page() {
  const [rows, setRows] = useState<Item[]>([]);
  useEffect(() => {
    api<Item[]>("/api/v1/vulnerabilities").then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div>
      <h1 className="text-3xl font-semibold">Vulnerabilities</h1>
      <p className="mt-2 text-[var(--fg-muted)]">V1 reports endpoint posture findings. This is not a CVE intelligence feed.</p>
      <div className="mt-8 space-y-3">
        {rows.length === 0 ? (
          <EmptyState title="No posture findings" body="Findings such as Defender or firewall disabled appear from agent posture telemetry." />
        ) : (
          rows.map((row) => (
            <div key={row.id} className="glass rounded-3xl p-5">
              <div className="flex items-center justify-between">
                <div className="text-lg">{row.title}</div>
                <Severity value={row.severity} />
              </div>
              <p className="mt-2 text-sm text-[var(--fg-muted)]">{row.description}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
