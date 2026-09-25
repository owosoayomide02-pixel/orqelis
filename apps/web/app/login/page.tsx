"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { AuthPanel, AuthShell } from "@/components/SiteChrome";
import { api } from "@/lib/api";

function safeNext(path: string | null): string {
  if (!path || !path.startsWith("/") || path.startsWith("//")) return "/dashboard";
  return path;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeNext(searchParams.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [mfa, setMfa] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const result = await api<{ mfa_required?: boolean }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, totp }),
      });
      if (result.mfa_required) {
        setMfa(true);
        return;
      }
      router.push(nextPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <AuthShell
      title="Sign in to your tenant"
      panel={
        <AuthPanel
          heading="Dashboard access"
          points={[
            { title: "Session cookies", body: "Human APIs use secure session cookies. Agent device tokens are separate and never interchangeable." },
            { title: "Role-aware views", body: "Overview, devices, alerts, incidents, vulnerabilities, AI assist, reports, and billing live behind this login." },
            { title: "MFA ready", body: "If authenticator MFA is enabled on your account, Orqelis asks for a one-time code after password verification." },
            { title: "Audit trail", body: "Sensitive actions and approvals are recorded for operator accountability." },
          ]}
          next={[
            { title: "Land on Overview", body: "See the Orqelis score, open findings, and first-run checklist if no agent is enrolled yet." },
            { title: "Manage endpoints", body: "Create enrollment codes and confirm agents report only listed security telemetry." },
            { title: "Act on detections", body: "Review alerts/incidents and approve or reject supported remediation actions." },
          ]}
        />
      }
    >
      <form onSubmit={onSubmit}>
        <p className="mb-5 text-sm leading-6 text-[var(--fg-muted)]">
          Enter your Orqelis credentials to open the customer security console.
        </p>
        <label className="block text-sm text-[var(--fg-muted)]" htmlFor="email">
          Email
        </label>
        <input id="email" className="mt-1.5" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label className="mt-4 block text-sm text-[var(--fg-muted)]" htmlFor="password">
          Password
        </label>
        <input id="password" className="mt-1.5" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {mfa ? (
          <>
            <label className="mt-4 block text-sm text-[var(--fg-muted)]" htmlFor="totp">
              Authenticator code
            </label>
            <input id="totp" className="mt-1.5" inputMode="numeric" autoComplete="one-time-code" value={totp} onChange={(e) => setTotp(e.target.value)} required />
            <p className="mt-1.5 text-xs text-[var(--fg-muted)]">Open your authenticator app and enter the current 6-digit code.</p>
          </>
        ) : null}
        {error ? <p className="mt-4 text-sm text-[var(--critical)]">{error}</p> : null}
        <button className="btn btn-primary mt-5 w-full" type="submit">
          {mfa ? "Verify and continue" : "Enter dashboard"}
        </button>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm text-[var(--fg-muted)]">
          <Link href="/register" className="underline underline-offset-2">
            Create an account
          </Link>
          <Link href="/reset-password" className="underline underline-offset-2">
            Forgot password
          </Link>
          <Link href="/security" className="underline underline-offset-2">
            Security practices
          </Link>
        </div>
      </form>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <LoginForm />
    </Suspense>
  );
}
