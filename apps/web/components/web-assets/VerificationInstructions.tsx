"use client";

import { useEffect, useState } from "react";
import type { WebAsset } from "@/lib/api";
import { verifyWebAsset } from "@/lib/api";

export function VerificationInstructions({
  asset,
  onVerified,
}: {
  asset: WebAsset;
  onVerified: (asset: WebAsset) => void;
}) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const instructions = asset.verification_instructions;

  async function check(testMode = false) {
    setBusy(true);
    setMessage("");
    try {
      const result = await verifyWebAsset(asset.id, testMode);
      if (result.verification_status === "verified") {
        onVerified(result);
      } else {
        setMessage(result.message || "TXT record not found yet.");
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (asset.verification_status === "verified") return;
    const onFocus = () => {
      if (document.visibilityState === "visible") check(false);
    };
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") check(false);
    }, 10000);
    document.addEventListener("visibilitychange", onFocus);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onFocus);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asset.id, asset.verification_status]);

  if (!instructions || asset.verification_status === "verified") {
    return (
      <div className="glass rounded-3xl p-5 text-sm text-[var(--success)]">
        Verified{asset.verified_at ? ` · ${asset.verified_at}` : ""}
      </div>
    );
  }

  return (
    <div className="glass rounded-3xl p-5">
      <h3 className="text-lg">Prove ownership</h3>
      <p className="mt-2 text-sm text-[var(--fg-muted)]">
        Add this DNS TXT record, then check verification. Propagation can take up to 24 hours.
      </p>
      <dl className="mt-4 space-y-2 font-mono-tech text-sm">
        <div>
          <dt className="text-[var(--fg-muted)]">Type</dt>
          <dd>{instructions.record_type}</dd>
        </div>
        <div>
          <dt className="text-[var(--fg-muted)]">Name</dt>
          <dd className="break-all">{instructions.record_name}</dd>
        </div>
        <div>
          <dt className="text-[var(--fg-muted)]">Value</dt>
          <dd className="break-all">{instructions.record_value}</dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-3">
        <button className="btn btn-primary" type="button" disabled={busy} onClick={() => check(false)}>
          {busy ? "Checking…" : "Check now"}
        </button>
        {process.env.NODE_ENV !== "production" ? (
          <button className="btn" type="button" disabled={busy} onClick={() => check(true)}>
            Test-mode verify
          </button>
        ) : null}
      </div>
      {message ? <p className="mt-3 text-sm text-[var(--warning)]">{message}</p> : null}
    </div>
  );
}
