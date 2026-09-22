"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const verifyRef = useRef<HTMLDivElement>(null);
  const [form, setForm] = useState({
    email: "",
    password: "",
    display_name: "",
    organization_name: "",
    accept_terms: false,
    acknowledge_privacy: false,
    marketing_opt_in: false,
  });
  const [error, setError] = useState("");
  const [verifyUrl, setVerifyUrl] = useState("");

  useEffect(() => {
    if (verifyUrl) verifyRef.current?.focus();
  }, [verifyUrl]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const result = await api<{ verification_url?: string }>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(form) });
      if (result.verification_url) {
        setVerifyUrl(result.verification_url);
        return;
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto w-full max-w-lg px-6">
        <form onSubmit={onSubmit} className="glass mx-auto mt-12 rounded-3xl p-8">
          <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">ORQELIS</div>
          <h1 className="mt-2 text-2xl">Get started</h1>
          <label className="mt-6 block text-sm text-[var(--fg-muted)]" htmlFor="display_name">
            Name
          </label>
          <input id="display_name" className="mt-2" autoComplete="name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          <label className="mt-4 block text-sm text-[var(--fg-muted)]" htmlFor="organization_name">
            Organization
          </label>
          <input id="organization_name" className="mt-2" autoComplete="organization" value={form.organization_name} onChange={(e) => setForm({ ...form, organization_name: e.target.value })} />
          <label className="mt-4 block text-sm text-[var(--fg-muted)]" htmlFor="email">
            Email
          </label>
          <input id="email" className="mt-2" type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <label className="mt-4 block text-sm text-[var(--fg-muted)]" htmlFor="password">
            Password (8+ characters)
          </label>
          <input id="password" className="mt-2" type="password" autoComplete="new-password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <div className="mt-5 flex items-start gap-3 text-sm text-[var(--fg-muted)]">
            <input id="accept_terms" type="checkbox" className="mt-1 w-auto shrink-0" checked={form.accept_terms} onChange={(e) => setForm({ ...form, accept_terms: e.target.checked })} required />
            <div>
              <label htmlFor="accept_terms">I agree to the Orqelis Terms of Service.</label>{" "}
              <Link href="/docs/terms" className="underline underline-offset-2">
                Read terms
              </Link>
            </div>
          </div>
          <div className="mt-3 flex items-start gap-3 text-sm text-[var(--fg-muted)]">
            <input id="acknowledge_privacy" type="checkbox" className="mt-1 w-auto shrink-0" checked={form.acknowledge_privacy} onChange={(e) => setForm({ ...form, acknowledge_privacy: e.target.checked })} required />
            <div>
              <label htmlFor="acknowledge_privacy">I acknowledge the Orqelis Privacy Policy.</label>{" "}
              <Link href="/docs/privacy" className="underline underline-offset-2">
                Read privacy policy
              </Link>
            </div>
          </div>
          <div className="mt-3 flex items-start gap-3 text-sm text-[var(--fg-muted)]">
            <input id="marketing_opt_in" type="checkbox" className="mt-1 w-auto shrink-0" checked={form.marketing_opt_in} onChange={(e) => setForm({ ...form, marketing_opt_in: e.target.checked })} />
            <label htmlFor="marketing_opt_in">Send me occasional product updates (optional).</label>
          </div>
          {error ? (
            <p className="mt-4 text-sm text-[var(--critical)]" role="alert">
              {error}
            </p>
          ) : null}
          {verifyUrl ? (
            <div ref={verifyRef} tabIndex={-1} className="mt-5 rounded-2xl border border-[var(--warning)] p-4 text-sm outline-none" aria-live="polite">
              <div>Account created. SMTP is unset, so verify with this development link:</div>
              <a className="mt-2 block break-all text-[var(--brand)]" href={verifyUrl}>
                {verifyUrl}
              </a>
              <button className="btn btn-primary mt-4 w-full" type="button" onClick={() => router.push("/dashboard")}>
                Continue to dashboard
              </button>
            </div>
          ) : (
            <button className="btn btn-primary mt-6 w-full" type="submit">
              Create account
            </button>
          )}
        </form>
      </main>
      <SiteFooter />
    </div>
  );
}
