"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { api } from "@/lib/api";

function VerifyInner() {
  const params = useSearchParams();
  const [message, setMessage] = useState("Verifying…");
  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setMessage("Missing token.");
      return;
    }
    api("/api/v1/auth/verify-email", { method: "POST", body: JSON.stringify({ token }) })
      .then(() => setMessage("Email verified. You can close this page."))
      .catch((err) => setMessage(err instanceof Error ? err.message : "Verification failed"));
  }, [params]);
  return <p className="mt-8 text-[var(--fg-muted)]">{message}</p>;
}

export default function Page() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-lg px-6 py-20">
        <h1 className="text-3xl">Verify email</h1>
        <Suspense>
          <VerifyInner />
        </Suspense>
      </main>
      <SiteFooter />
    </div>
  );
}
