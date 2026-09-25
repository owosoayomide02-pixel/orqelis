"use client";

import { severityColor } from "@/lib/nav";
import type { Finding } from "@/lib/api";

export function FindingsList({
  findings,
  loading,
  error,
  onAnalyze,
  onFix,
}: {
  findings: Finding[];
  loading?: boolean;
  error?: string;
  onAnalyze?: (id: string) => void;
  onFix?: (id: string) => void;
}) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass h-16 animate-pulse rounded-2xl" />
        ))}
      </div>
    );
  }
  if (error) {
    return <p className="text-sm text-[var(--critical)]">{error}</p>;
  }
  if (!findings.length) {
    return (
      <div className="glass rounded-3xl p-6 text-sm text-[var(--fg-muted)]">
        No findings yet. Run Hunter after the domain is verified.
      </div>
    );
  }
  return (
    <ul className="space-y-3">
      {findings.map((f, index) => (
        <li
          key={f.id}
          className="glass orqelis-finding-enter rounded-2xl p-4"
          style={{ animationDelay: `${index * 120}ms` }}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">{f.title}</span>
                {f.auto_detected || f.detection_source === "sentinel" ? (
                  <span className="rounded bg-[var(--bg-info)] px-2 py-0.5 text-[10px] uppercase tracking-wider text-[var(--text-info)]">
                    auto-detected
                  </span>
                ) : null}
              </div>
              <p className="mt-1 font-mono-tech text-xs" style={{ color: severityColor(f.severity) }}>
                {f.severity}
                {typeof f.risk_score === "number" ? ` · risk ${f.risk_score}` : ""}
              </p>
            </div>
            <div className="flex gap-2">
              {onAnalyze ? (
                <button className="btn" type="button" onClick={() => onAnalyze(f.id)}>
                  Analyst
                </button>
              ) : null}
              {onFix ? (
                <button className="btn" type="button" onClick={() => onFix(f.id)}>
                  Fixer
                </button>
              ) : null}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
