"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FindingsList } from "@/components/web-assets/FindingsList";
import { FixSuggestion } from "@/components/web-assets/FixSuggestion";
import { RoleSelector } from "@/components/web-assets/RoleSelector";
import { ScanProgress } from "@/components/web-assets/ScanProgress";
import { VerificationInstructions } from "@/components/web-assets/VerificationInstructions";
import {
  analyzeFinding,
  fixFinding,
  generateReport,
  getFindings,
  getWebAsset,
  listScans,
  startScan,
  type Finding,
  type FixerResult,
  type ScanJob,
  type WebAsset,
} from "@/lib/api";

export default function WebAssetDetailPage() {
  const params = useParams();
  const id = String(params.id || "");
  const [asset, setAsset] = useState<WebAsset | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [scans, setScans] = useState<ScanJob[]>([]);
  const [scanJobId, setScanJobId] = useState<string | null>(null);
  const [activeRole, setActiveRole] = useState<string>("sentinel");
  const [fix, setFix] = useState<FixerResult | null>(null);
  const [analysis, setAnalysis] = useState("");
  const [roleHint, setRoleHint] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    const [a, f, s] = await Promise.all([getWebAsset(id), getFindings(id), listScans(id)]);
    setAsset(a);
    setFindings(f);
    setScans(s);
  }, [id]);

  useEffect(() => {
    reload()
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [reload]);

  async function onRole(role: string) {
    setActiveRole(role);
    setError("");
    setRoleHint("");
    if (!asset) return;
    try {
      if (role === "hunter") {
        const res = await startScan(asset.id, "hunter");
        setScanJobId(res.scan_job_id);
      } else if (role === "auditor") {
        const res = await generateReport(asset.id);
        window.location.href = `/dashboard/web-assets/${asset.id}/report?report=${res.report_job_id}`;
      } else if (role === "sentinel") {
        setRoleHint(
          "Sentinel watches passively. After Hunter finds high/critical issues, Sentinel auto-triages them (tagged auto-detected).",
        );
      } else if (role === "analyst") {
        setRoleHint("Pick a finding below and click Analyst for a plain-language explanation.");
      } else if (role === "fixer") {
        setRoleHint("Pick a finding below and click Fixer for a remediation draft (never auto-applied).");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  }

  if (loading) {
    return <div className="glass mt-8 h-40 animate-pulse rounded-3xl" />;
  }
  if (!asset) {
    return <p className="text-[var(--critical)]">{error || "Not found"}</p>;
  }

  const verified = asset.verification_status === "verified";
  const risk = findings.reduce((max, f) => Math.max(max, f.risk_score || 0), 0);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/dashboard/web-assets" className="text-xs text-[var(--fg-muted)]">
            ← Web assets
          </Link>
          <h1 className="mt-2 font-mono-tech text-3xl">{asset.domain}</h1>
          <p className="mt-2 text-sm text-[var(--fg-muted)]">Status: {asset.verification_status}</p>
        </div>
        <div className="glass rounded-2xl px-5 py-3 text-center">
          <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--fg-muted)]">Risk score</div>
          <div className="mt-1 text-3xl font-mono-tech" style={{ color: risk >= 70 ? "var(--critical)" : "var(--accent)" }}>
            {risk}
          </div>
        </div>
      </div>

      <VerificationInstructions asset={asset} onVerified={setAsset} />

      <div>
        <h2 className="mb-3 text-lg">AI roles</h2>
        <RoleSelector verified={verified} active={activeRole} onSelect={onRole} disabled={!!scanJobId} />
        {roleHint ? <p className="mt-3 text-sm text-[var(--fg-muted)]">{roleHint}</p> : null}
      </div>

      {error ? <p className="text-sm text-[var(--critical)]">{error}</p> : null}

      {scanJobId ? (
        <ScanProgress
          webAssetId={asset.id}
          scanJobId={scanJobId}
          onDone={async () => {
            setScanJobId(null);
            await reload();
          }}
        />
      ) : null}

      {analysis ? (
        <div className="glass rounded-3xl p-5 text-sm">
          <h3 className="text-lg">Analyst</h3>
          <p className="mt-2">{analysis}</p>
        </div>
      ) : null}

      <FixSuggestion fix={fix} />

      <div>
        <h2 className="mb-3 text-lg">Findings</h2>
        <FindingsList
          findings={findings}
          onAnalyze={async (fid) => {
            try {
              const res = await analyzeFinding(fid);
              setAnalysis(res.explanation);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Analyze failed");
            }
          }}
          onFix={async (fid) => {
            try {
              setFix(await fixFinding(fid));
            } catch (err) {
              setError(err instanceof Error ? err.message : "Fix failed");
            }
          }}
        />
      </div>

      {scans.length ? (
        <div>
          <h2 className="mb-3 text-lg">Scan history</h2>
          <ul className="space-y-2 font-mono-tech text-sm text-[var(--fg-muted)]">
            {scans.map((s) => (
              <li key={s.id}>
                {s.id.slice(0, 8)} · {s.status} · {s.findings_count} findings
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
