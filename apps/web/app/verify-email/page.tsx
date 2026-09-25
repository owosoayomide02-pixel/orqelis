"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AuthPanel, AuthShell } from "@/components/SiteChrome";
import { api } from "@/lib/api";

function VerifyInner() {
  const params = useSearchParams();
  const [message, setMessage] = useState("Verifying your email address…");
  const [ok, setOk] = useState(false);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setMessage("Missing verification token. Open the link from your registration email or development API log.");
      return;
    }
    api("/api/v1/auth/verify-email", { method: "POST", body: JSON.stringify({ token }) })
      .then(() => {
        setOk(true);
        setMessage("Email verified. Your account can use the full customer dashboard.");
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "Verification failed"));
  }, [params]);

  return (
    <AuthShell
      title="Verify email"
      panel={
        <AuthPanel
          heading="Why we verify"
          points={[
            { title: "Account ownership", body: "Confirming email reduces account takeover risk and keeps recovery flows trustworthy." },
            { title: "Tenant notifications", body: "Security notices and billing messages go to a mailbox you control." },
            { title: "Development mode", body: "When SMTP is unset, registration returns a local verification URL instead of sending mail." },
            { title: "Still blocked?", body: "Request a fresh link from the dashboard banner after signing in, or re-register if the token expired." },
          ]}
        />
      }
    >
      <div className={`rounded-xl border p-4 text-sm leading-6 ${ok ? "border-[var(--success)] text-[var(--fg)]" : "border-[var(--line)] text-[var(--fg-muted)]"}`}>
        {message}
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        <Link href="/login" className="btn btn-primary">
          Go to login
        </Link>
        <Link href="/dashboard" className="btn btn-ghost">
          Open dashboard
        </Link>
      </div>
    </AuthShell>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen p-8 text-[var(--fg-muted)]">Preparing verification…</div>}>
      <VerifyInner />
    </Suspense>
  );
}
