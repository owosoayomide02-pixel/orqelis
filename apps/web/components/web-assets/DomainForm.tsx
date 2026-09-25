"use client";

import { FormEvent, useState } from "react";

const DOMAIN_RE = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$/;

export function DomainForm({
  onSubmit,
  busy,
}: {
  onSubmit: (domain: string) => Promise<void>;
  busy?: boolean;
}) {
  const [domain, setDomain] = useState("");
  const [error, setError] = useState("");

  async function handle(e: FormEvent) {
    e.preventDefault();
    const value = domain.trim().toLowerCase().replace(/^https?:\/\//, "").split("/")[0];
    if (!DOMAIN_RE.test(value)) {
      setError("Enter a valid public domain (example.com)");
      return;
    }
    setError("");
    await onSubmit(value);
  }

  return (
    <form onSubmit={handle} className="glass max-w-xl rounded-3xl p-6">
      <label className="text-xs tracking-[0.2em] text-[var(--fg-muted)]" htmlFor="domain">
        DOMAIN
      </label>
      <input
        id="domain"
        className="mt-2 w-full font-mono-tech"
        placeholder="acme-app.com"
        value={domain}
        onChange={(e) => setDomain(e.target.value)}
        required
      />
      {error ? <p className="mt-2 text-sm text-[var(--critical)]">{error}</p> : null}
      <button className="btn btn-primary mt-4" type="submit" disabled={busy}>
        {busy ? "Adding…" : "Add domain"}
      </button>
    </form>
  );
}
