"use client";

import Link from "next/link";
import { FormEvent, Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AuthPanel, AuthShell } from "@/components/SiteChrome";
import { api } from "@/lib/api";

function ResetInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      if (token) {
        await api("/api/v1/auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token, password }) });
        setDone("Password updated. You can log in with the new credentials.");
        return;
      }
      const result = await api<{ reset_url?: string }>("/api/v1/auth/password-reset/request", { method: "POST", body: JSON.stringify({ email }) });
      setDone(result.reset_url || "If the account exists, a reset link was issued. In development it is also printed in the API log.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset request failed");
    }
  }

  return (
    <AuthShell
      title={token ? "Choose a new password" : "Reset your password"}
      panel={
        <AuthPanel
          heading="Account recovery"
          points={[
            { title: "Email-based flow", body: "Request a one-time reset link for the address on your Orqelis account." },
            { title: "Dev fallback", body: "When SMTP is unset, the API returns or logs a development reset URL instead of sending mail." },
            { title: "Session safety", body: "After confirming a new password, sign in again from the login page." },
            { title: "Need help?", body: "Contact [SUPPORT EMAIL] if you no longer control the registered mailbox." },
          ]}
          next={[
            { title: "Request or set password", body: token ? "Submit a strong new password (≥ 8 characters)." : "Enter the email used at registration." },
            { title: "Complete the link", body: "Open the reset URL from email or the API log when SMTP is disabled." },
            { title: "Return to login", body: "Sign in and continue to your tenant dashboard." },
          ]}
        />
      }
    >
      <form onSubmit={onSubmit}>
        <p className="mb-5 text-sm leading-6 text-[var(--fg-muted)]">
          {token
            ? "You opened a password-reset link. Choose a new password for this account."
            : "We’ll issue a reset link if an account exists for that email. No account details are revealed either way."}
        </p>
        {token ? (
          <>
            <label className="block text-sm text-[var(--fg-muted)]" htmlFor="password">
              New password
            </label>
            <input id="password" className="mt-1.5" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
          </>
        ) : (
          <>
            <label className="block text-sm text-[var(--fg-muted)]" htmlFor="email">
              Account email
            </label>
            <input id="email" className="mt-1.5" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </>
        )}
        {error ? <p className="mt-4 text-sm text-[var(--critical)]">{error}</p> : null}
        <button className="btn btn-primary mt-5 w-full" type="submit">
          {token ? "Update password" : "Send reset link"}
        </button>
        {done ? <p className="mt-4 break-all text-sm text-[var(--fg-muted)]">{done}</p> : null}
        <p className="mt-4 text-sm text-[var(--fg-muted)]">
          <Link href="/login" className="underline underline-offset-2">
            Back to login
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen p-8 text-[var(--fg-muted)]">Loading reset form…</div>}>
      <ResetInner />
    </Suspense>
  );
}
