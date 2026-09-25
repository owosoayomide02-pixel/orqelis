"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { DomainForm } from "@/components/web-assets/DomainForm";
import { createWebAsset } from "@/lib/api";

export default function NewWebAssetPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  return (
    <div>
      <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">WEB ASSETS</div>
      <h1 className="mt-2 text-3xl">Add domain</h1>
      <p className="mt-2 max-w-xl text-sm text-[var(--fg-muted)]">
        Public hostnames only — no IPs or internal ranges.
      </p>
      <div className="mt-8">
        <DomainForm
          busy={busy}
          onSubmit={async (domain) => {
            setBusy(true);
            setError("");
            try {
              const asset = await createWebAsset(domain);
              router.push(`/dashboard/web-assets/${asset.id}`);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Could not add domain");
              setBusy(false);
            }
          }}
        />
      </div>
      {error ? <p className="mt-4 text-sm text-[var(--critical)]">{error}</p> : null}
    </div>
  );
}
