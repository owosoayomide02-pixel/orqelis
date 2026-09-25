"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/DashboardShell";
import { listWebAssets, type WebAsset } from "@/lib/api";

export default function WebAssetsPage() {
  const [rows, setRows] = useState<WebAsset[]>([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listWebAssets()
      .then(setRows)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setReady(true));
  }, []);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">WEB ASSETS</div>
          <h1 className="mt-2 text-3xl">Domains</h1>
          <p className="mt-2 max-w-xl text-sm text-[var(--fg-muted)]">
            Verify ownership, then run Hunter scans. Findings feed the same alert pipeline as devices.
          </p>
        </div>
        <Link className="btn btn-primary" href="/dashboard/web-assets/new">
          Add domain
        </Link>
      </div>

      {error ? <p className="mt-6 text-sm text-[var(--critical)]">{error}</p> : null}

      {!ready ? (
        <div className="mt-8 space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="glass h-14 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : null}

      {ready && !rows.length && !error ? (
        <div className="mt-8">
          <EmptyState
            title="No domains yet"
            body="Add your first public domain, prove ownership with a DNS TXT record, then choose an AI role."
          />
          <Link className="btn btn-primary mt-4 inline-flex" href="/dashboard/web-assets/new">
            Add your first domain
          </Link>
        </div>
      ) : null}

      {rows.length ? (
        <ul className="mt-8 space-y-3">
          {rows.map((row) => (
            <li key={row.id}>
              <Link
                href={`/dashboard/web-assets/${row.id}`}
                className="glass flex items-center justify-between rounded-2xl p-4 hover:border-[var(--accent)]"
              >
                <span className="font-mono-tech">{row.domain}</span>
                <span
                  className={`text-xs uppercase tracking-wider ${
                    row.verification_status === "verified" ? "text-[var(--success)]" : "text-[var(--warning)]"
                  }`}
                >
                  {row.verification_status}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
