"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { getReport } from "@/lib/api";

function ReportBody() {
  const params = useParams();
  const search = useSearchParams();
  const assetId = String(params.id || "");
  const reportId = search.get("report") || "";
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!reportId) {
      setError("Missing report id");
      return;
    }
    getReport(assetId, reportId)
      .then((r) => {
        setTitle(r.title);
        setBody(r.body_markdown);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load report"));
  }, [assetId, reportId]);

  return (
    <div>
      <Link href={`/dashboard/web-assets/${assetId}`} className="text-xs text-[var(--fg-muted)]">
        ← Back to asset
      </Link>
      <h1 className="mt-2 text-3xl">{title || "Auditor report"}</h1>
      {error ? <p className="mt-4 text-[var(--critical)]">{error}</p> : null}
      <article className="glass mt-8 max-w-none whitespace-pre-wrap rounded-3xl p-6 text-sm">
        {body || (error ? "" : "Loading…")}
      </article>
      <button className="btn btn-primary mt-6" type="button" onClick={() => window.print()}>
        Download as PDF
      </button>
    </div>
  );
}

export default function WebAssetReportPage() {
  return (
    <Suspense fallback={<div className="glass h-40 animate-pulse rounded-3xl" />}>
      <ReportBody />
    </Suspense>
  );
}
