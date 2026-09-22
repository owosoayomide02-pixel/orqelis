"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const ROLES = ["analyst", "sentinel", "fixer"] as const;

type Analysis = {
  id: string;
  role: string;
  provider: string;
  output: { explanation?: string; recommended_remediation?: string[] };
};

export function RunAI({ subjectType, subjectId }: { subjectType: string; subjectId: string }) {
  const [role, setRole] = useState<(typeof ROLES)[number]>("analyst");
  const [result, setResult] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError("");
    try {
      const row = await api<Analysis>("/api/v1/ai/analyze", {
        method: "POST",
        body: JSON.stringify({ role, subject_type: subjectType, subject_id: subjectId }),
      });
      setResult(row);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="glass mt-6 rounded-3xl p-5">
      <div className="text-sm uppercase tracking-wide text-[var(--ai)]">AI Security Team</div>
      <div className="mt-3 flex flex-wrap gap-2">
        {ROLES.map((item) => (
          <button key={item} className={`rounded-full border border-[var(--line)] px-3 py-1 text-sm ${role === item ? "text-[var(--ai)]" : "text-[var(--fg-muted)]"}`} onClick={() => setRole(item)}>
            {item}
          </button>
        ))}
        <button className="btn btn-primary !py-2" onClick={run} disabled={busy}>
          {busy ? "Running…" : `Run ${role}`}
        </button>
      </div>
      {error ? <p className="mt-3 text-sm text-[var(--critical)]">{error}</p> : null}
      {result ? (
        <div className="mt-4 text-sm text-[var(--fg-muted)]">
          <div className="uppercase tracking-wide text-[var(--ai)]">
            {result.role} · {result.provider}
          </div>
          <p className="mt-2">{result.output?.explanation}</p>
        </div>
      ) : null}
    </div>
  );
}

export function PostureList({ items }: { items: { id: string; label: string; ok: boolean; detail: string; skip?: boolean }[] }) {
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.id} className="glass flex items-start justify-between rounded-2xl p-4">
          <div>
            <div>{item.label}</div>
            <div className="text-sm text-[var(--fg-muted)]">{item.detail}</div>
          </div>
          <div className="text-sm uppercase tracking-wide" style={{ color: item.skip ? "var(--fg-muted)" : item.ok ? "var(--success)" : "var(--critical)" }}>
            {item.skip ? "n/a" : item.ok ? "ok" : "fix"}
          </div>
        </div>
      ))}
    </div>
  );
}
