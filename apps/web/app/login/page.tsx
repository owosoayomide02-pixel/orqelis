"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
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
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <form onSubmit={onSubmit} className="glass mx-auto mt-16 w-full max-w-md rounded-3xl p-8">
        <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">ORQELIS</div>
        <h1 className="mt-2 text-2xl">Login</h1>
        <label className="mt-6 block text-sm text-[var(--fg-muted)]">Email</label>
        <input className="mt-2" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label className="mt-4 block text-sm text-[var(--fg-muted)]">Password</label>
        <input className="mt-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {mfa ? (
          <>
            <label className="mt-4 block text-sm text-[var(--fg-muted)]">Authenticator code</label>
            <input className="mt-2" inputMode="numeric" autoComplete="one-time-code" value={totp} onChange={(e) => setTotp(e.target.value)} required />
          </>
        ) : null}
        {error ? <p className="mt-4 text-sm text-[var(--critical)]">{error}</p> : null}
        <button className="btn btn-primary mt-6 w-full" type="submit">
          {mfa ? "Verify" : "Enter"}
        </button>
        <p className="mt-4 text-sm text-[var(--fg-muted)]">
          No account? <Link href="/register">Get started</Link>
          {" · "}
          <Link href="/reset-password">Forgot password</Link>
        </p>
      </form>
      <SiteFooter />
    </div>
  );
}
