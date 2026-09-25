"use client";

import { useEffect, useState } from "react";
import type { ScanJob } from "@/lib/api";
import { getScanStatus } from "@/lib/api";

export function ScanProgress({
  webAssetId,
  scanJobId,
  onDone,
}: {
  webAssetId: string;
  scanJobId: string;
  onDone: (job: ScanJob) => void;
}) {
  const [job, setJob] = useState<ScanJob | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const next = await getScanStatus(webAssetId, scanJobId);
        if (cancelled) return;
        setJob(next);
        if (next.status === "queued" || next.status === "running") {
          window.setTimeout(poll, 3500);
        } else {
          onDone(next);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not read scan status");
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [webAssetId, scanJobId, onDone]);

  return (
    <div className="glass orqelis-scanline rounded-3xl p-5">
      <h3 className="text-lg">Hunter scan</h3>
      {!job && !error ? <p className="mt-2 text-sm text-[var(--fg-muted)]">Starting…</p> : null}
      {error ? <p className="mt-2 text-sm text-[var(--critical)]">{error}</p> : null}
      {job ? (
        <div className="mt-3 space-y-2 text-sm">
          <p>
            Status: <span className="font-mono-tech">{job.status}</span>
            {job.current_tool ? (
              <>
                {" "}
                · tool <span className="font-mono-tech">{job.current_tool}</span>
              </>
            ) : null}
          </p>
          <p className="font-mono-tech text-[var(--fg-muted)]">
            tools: {(job.tools_run || []).join(", ") || "—"} · findings: {job.findings_count}
          </p>
          {job.error_message ? <p className="text-[var(--warning)]">{job.error_message}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
