"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";

type Overview = {
  organizations: number;
  users: number;
  devices: number;
  alerts_processed: number;
  active_subscriptions: number;
  environment?: string;
  api_ok?: boolean;
  agent_versions?: { platform: string; version: string; notes: string }[];
  system_incidents?: { id: string; title: string; status: string; severity: string }[];
  ai: { requests: number; prompt_tokens: number; estimated_cost_cents: number };
  note: string;
  viewer: { role: string; email?: string };
};
type Audit = { id: string; action: string; actor_type: string; created_at: string };

export default function Page() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [me, setMe] = useState<{ email: string; role: string } | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [error, setError] = useState("");

  async function load() {
    const user = await api<{ email: string; role: string }>("/api/v1/admin/me");
    setMe(user);
    setOverview(await api<Overview>("/api/v1/admin/overview"));
    setAudit(await api<Audit[]>("/api/v1/admin/audit"));
  }

  useEffect(() => {
    load().catch(() => setMe(null));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/admin/login", { method: "POST", body: JSON.stringify({ email, password }) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  if (!me) {
    return (
      <form onSubmit={onSubmit} className="glass mx-auto mt-24 max-w-md rounded-3xl p-8">
        <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">FOUNDER CONSOLE</div>
        <h1 className="mt-2 text-2xl">Orqelis</h1>
        <p className="mt-3 text-sm text-[var(--fg-muted)]">Internal roles only. This is not a customer telemetry browser.</p>
        <input className="mt-6" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="mt-3" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error ? <p className="mt-3 text-sm text-[#ff3b5c]">{error}</p> : null}
        <button className="btn mt-6 w-full" type="submit">
          Sign in
        </button>
      </form>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">FOUNDER CONSOLE</div>
          <h1 className="mt-2 text-3xl">Platform health</h1>
          <p className="mt-2 text-sm text-[var(--fg-muted)]">
            {me.email} · {me.role}
          </p>
        </div>
        <button
          onClick={async () => {
            await api("/api/v1/admin/logout", { method: "POST" });
            setMe(null);
            setOverview(null);
          }}
        >
          Sign out
        </button>
      </div>
      {overview ? (
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ["Organizations", overview.organizations],
            ["Users", overview.users],
            ["Devices", overview.devices],
            ["Alerts processed", overview.alerts_processed],
            ["Active subscriptions", overview.active_subscriptions],
            ["AI requests", overview.ai.requests],
            ["AI cost (cents)", overview.ai.estimated_cost_cents],
            ["Environment", overview.environment || "development"],
          ].map(([label, value]) => (
            <div key={String(label)} className="glass rounded-3xl p-5">
              <div className="text-xs uppercase tracking-wide text-[var(--fg-muted)]">{label}</div>
              <div className="mt-2 text-3xl">{value}</div>
            </div>
          ))}
        </div>
      ) : null}
      <p className="mt-6 text-sm text-[var(--fg-muted)]">{overview?.note}</p>
      <h2 className="mt-10 text-xl">Agent versions</h2>
      <div className="mt-4 space-y-2">
        {(overview?.agent_versions || []).map((row) => (
          <div key={row.platform} className="glass rounded-2xl p-4 text-sm text-[var(--fg-muted)]">
            {row.platform} · {row.version} · {row.notes}
          </div>
        ))}
      </div>
      <h2 className="mt-10 text-xl">System incidents</h2>
      <div className="mt-4 space-y-2">
        {(overview?.system_incidents || []).length === 0 ? (
          <div className="text-sm text-[var(--fg-muted)]">No platform incidents recorded.</div>
        ) : (
          (overview?.system_incidents || []).map((row) => (
            <div key={row.id} className="glass rounded-2xl p-4 text-sm text-[var(--fg-muted)]">
              {row.severity} · {row.status} · {row.title}
            </div>
          ))
        )}
      </div>
      <h2 className="mt-10 text-xl">Audit</h2>
      <div className="mt-4 space-y-2">
        {audit.map((row) => (
          <div key={row.id} className="glass rounded-2xl p-4 text-sm text-[var(--fg-muted)]">
            {row.created_at} · {row.actor_type} · {row.action}
          </div>
        ))}
      </div>
    </main>
  );
}
