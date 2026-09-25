"use client";

import type { FixerResult } from "@/lib/api";

export function FixSuggestion({ fix }: { fix: FixerResult | null }) {
  if (!fix) return null;
  return (
    <div className="glass rounded-3xl p-5">
      <h3 className="text-lg">Fixer suggestion</h3>
      <p className="mt-2 text-sm text-[var(--warning)]">This has not been applied. Human approval required.</p>
      <p className="mt-3 text-sm">{fix.description}</p>
      <pre className="mt-4 overflow-x-auto rounded-xl bg-[var(--surface-0)] p-4 font-mono-tech text-xs">{fix.diff}</pre>
      <button className="btn mt-4 opacity-50" type="button" disabled title="GitHub App not configured">
        Open as PR
      </button>
    </div>
  );
}
