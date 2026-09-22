"use client";

import { FormEvent, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { api } from "@/lib/api";

function ResetInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (token) {
      await api("/api/v1/auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token, password }) });
      setDone("Password updated. You can log in.");
      return;
    }
    const result = await api<{ reset_url?: string }>("/api/v1/auth/password-reset/request", { method: "POST", body: JSON.stringify({ email }) });
    setDone(result.reset_url || "If the account exists, a reset link was issued. In development it is also printed in the API log.");
  }

  return (
    <form onSubmit={onSubmit} className="glass mx-auto mt-16 max-w-md rounded-3xl p-8">
      <h1 className="text-2xl">{token ? "Choose a new password" : "Reset password"}</h1>
      {token ? (
        <input className="mt-6" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="New password" />
      ) : (
        <input className="mt-6" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      )}
      <button className="btn btn-primary mt-6 w-full" type="submit">
        Continue
      </button>
      {done ? <p className="mt-4 text-sm text-[var(--fg-muted)]">{done}</p> : null}
    </form>
  );
}

export default function Page() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <Suspense>
        <ResetInner />
      </Suspense>
      <SiteFooter />
    </div>
  );
}
