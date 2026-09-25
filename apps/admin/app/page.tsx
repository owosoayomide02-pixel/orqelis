"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, setSupabaseAccessToken } from "@/lib/api";
import { createSupabaseBrowser, hasSupabaseConfig } from "@/lib/supabase";

type Money = { cents: number; currency: string; formatted: string };

type Me = {
  id: string;
  email: string;
  role: string;
  display_name: string;
  created_at?: string | null;
};

type Overview = {
  organizations: number;
  users: number;
  devices: number;
  alerts_processed: number;
  open_alerts: number;
  incidents: number;
  open_incidents: number;
  vulnerabilities: number;
  web_assets: number;
  active_subscriptions: number;
  trial_subscriptions: number;
  inactive_subscriptions: number;
  environment?: string;
  api_ok?: boolean;
  billing_live?: boolean;
  revenue: {
    mrr_cents: number;
    arr_cents: number;
    recognized_revenue_cents: number;
    ai_cost_cents: number;
    gross_margin_cents: number;
    mrr: Money;
    arr: Money;
    recognized_revenue: Money;
    ai_cost: Money;
    gross_margin: Money;
    paying_customers: number;
    arpu: Money;
    note: string;
  };
  plan_breakdown: {
    plan_code: string;
    plan_name: string;
    subscribers: number;
    mrr_cents: number;
    monthly_price_cents: number;
  }[];
  plans: { code: string; name: string; monthly_price_cents: number; contact_sales: boolean; price: Money }[];
  subscriptions: {
    id: string;
    organization_name: string;
    status: string;
    provider: string;
    plan_name: string | null;
    monthly_price_cents: number;
    updated_at: string | null;
  }[];
  transactions: {
    id: string;
    type: string;
    status: string;
    organization_name: string;
    plan_name: string | null;
    provider: string;
    amount: Money;
    created_at: string | null;
  }[];
  transaction_summary: { count: number; posted_volume: Money; providers: Record<string, number> };
  organizations_detail: {
    id: string;
    name: string;
    slug: string;
    members: number;
    devices: number;
    subscription_status: string;
    plan_name: string | null;
    mrr_cents: number;
    created_at: string | null;
  }[];
  recent_users: {
    id: string;
    email: string;
    display_name: string;
    email_verified: boolean;
    mfa_enabled: boolean;
    created_at: string | null;
  }[];
  agent_versions?: { platform: string; version: string; notes: string }[];
  system_incidents?: { id: string; title: string; status: string; severity: string; created_at?: string | null }[];
  ai: { requests: number; prompt_tokens: number; completion_tokens?: number; estimated_cost_cents: number; estimated_cost?: Money };
  note: string;
  viewer: { role: string; email?: string; display_name?: string; id?: string };
};

type Audit = {
  id: string;
  action: string;
  actor_type: string;
  resource_type?: string;
  created_at: string | null;
  details?: Record<string, unknown>;
};

function money(cents: number | undefined | null) {
  return `$${((cents || 0) / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function when(value?: string | null) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="glass rounded-2xl p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--fg-muted)]">{label}</div>
      <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
      {hint ? <div className="mt-1 text-xs text-[var(--fg-muted)]">{hint}</div> : null}
    </div>
  );
}

export default function Page() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [me, setMe] = useState<Me | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const supabaseEnabled = hasSupabaseConfig();

  async function load() {
    const user = await api<Me>("/api/v1/admin/me");
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
    setLoading(true);
    try {
      if (supabaseEnabled) {
        const supabase = createSupabaseBrowser();
        if (!supabase) throw new Error("Supabase is not configured");
        const { data, error: authError } = await supabase.auth.signInWithPassword({ email, password });
        if (authError) throw authError;
        const token = data.session?.access_token;
        if (!token) throw new Error("No Supabase session");
        setSupabaseAccessToken(token);
      } else {
        await api("/api/v1/admin/login", { method: "POST", body: JSON.stringify({ email, password }) });
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  if (!me) {
    return (
      <form onSubmit={onSubmit} className="glass mx-auto mt-16 max-w-md rounded-2xl p-7">
        <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">FOUNDER CONSOLE</div>
        <h1 className="mt-2 text-2xl font-semibold">Orqelis</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--fg-muted)]">
          Internal platform ops: tenants, revenue math, transactions, and health.
          {supabaseEnabled ? " Sign in with Supabase Auth." : ""}
        </p>
        <input className="mt-5" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="mt-3" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error ? <p className="mt-3 text-sm text-[#ff3b5c]">{error}</p> : null}
        <button className="btn mt-5 w-full" type="submit" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    );
  }

  const name = me.display_name || overview?.viewer.display_name || "Founder";
  const rev = overview?.revenue;

  return (
    <main className="mx-auto max-w-7xl px-5 py-6">
      <header className="glass flex flex-wrap items-start justify-between gap-4 rounded-2xl p-5">
        <div>
          <div className="text-xs tracking-[0.28em] text-[var(--fg-muted)]">FOUNDER CONSOLE</div>
          <h1 className="mt-1 text-3xl font-semibold">Welcome, {name}</h1>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-[var(--fg-muted)]">
            <span>
              <span className="text-[var(--fg)]">Name:</span> {name}
            </span>
            <span>
              <span className="text-[var(--fg)]">Email:</span> {me.email}
            </span>
            <span>
              <span className="text-[var(--fg)]">Role:</span> {me.role}
            </span>
            <span>
              <span className="text-[var(--fg)]">Auth:</span> {supabaseEnabled ? "Supabase" : "Session cookie"}
            </span>
            {me.created_at ? (
              <span>
                <span className="text-[var(--fg)]">Account since:</span> {when(me.created_at)}
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-xl border border-[var(--line)] px-3 py-2 text-xs text-[var(--fg-muted)]">
            Env: <span className="text-[var(--fg)]">{overview?.environment || "development"}</span>
            {" · "}
            API: <span className="text-[var(--fg)]">{overview?.api_ok ? "ok" : "down"}</span>
            {" · "}
            Billing: <span className="text-[var(--fg)]">{overview?.billing_live ? "live" : "dev provider"}</span>
          </div>
          <button
            className="btn !bg-transparent !px-4"
            style={{ border: "1px solid var(--line)" }}
            onClick={async () => {
              try {
                if (supabaseEnabled) {
                  const supabase = createSupabaseBrowser();
                  await supabase?.auth.signOut();
                  setSupabaseAccessToken(null);
                } else {
                  await api("/api/v1/admin/logout", { method: "POST" });
                }
              } finally {
                setMe(null);
                setOverview(null);
                setAudit([]);
              }
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      {overview && rev ? (
        <>
          <section className="mt-5">
            <h2 className="mb-3 text-sm font-medium uppercase tracking-[0.2em] text-[var(--fg-muted)]">Revenue</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="MRR" value={rev.mrr.formatted} hint={`${rev.paying_customers} paying customers`} />
              <Stat label="ARR" value={rev.arr.formatted} hint="MRR × 12" />
              <Stat label="Recognized / period" value={rev.recognized_revenue.formatted} hint="Activations + active billed plans" />
              <Stat label="Gross margin (MRR − AI)" value={rev.gross_margin.formatted} hint={`AI cost ${rev.ai_cost.formatted}`} />
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="ARPU" value={rev.arpu.formatted} hint="MRR / active subscriptions" />
              <Stat label="Active subscriptions" value={overview.active_subscriptions} hint={`${overview.trial_subscriptions} trial · ${overview.inactive_subscriptions} inactive`} />
              <Stat label="Transaction volume" value={overview.transaction_summary.posted_volume.formatted} hint={`${overview.transaction_summary.count} ledger rows`} />
              <Stat label="AI spend" value={overview.ai.estimated_cost?.formatted || money(overview.ai.estimated_cost_cents)} hint={`${overview.ai.requests} requests · ${overview.ai.prompt_tokens.toLocaleString()} prompt tokens`} />
            </div>
            <p className="mt-3 text-xs leading-5 text-[var(--fg-muted)]">{rev.note}</p>
          </section>

          <section className="mt-6">
            <h2 className="mb-3 text-sm font-medium uppercase tracking-[0.2em] text-[var(--fg-muted)]">Platform volume</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
              <Stat label="Organizations" value={overview.organizations} />
              <Stat label="Users" value={overview.users} />
              <Stat label="Devices" value={overview.devices} />
              <Stat label="Web assets" value={overview.web_assets} />
              <Stat label="Alerts" value={overview.alerts_processed} hint={`${overview.open_alerts} open`} />
              <Stat label="Incidents" value={overview.incidents} hint={`${overview.open_incidents} open`} />
              <Stat label="Vulnerabilities" value={overview.vulnerabilities} />
              <Stat label="AI requests" value={overview.ai.requests} />
            </div>
          </section>

          <section className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="glass rounded-2xl p-4">
              <h2 className="text-lg font-medium">Plan mix</h2>
              <p className="mt-1 text-xs text-[var(--fg-muted)]">Active paid seats by catalog plan</p>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[420px] text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-[var(--fg-muted)]">
                    <tr>
                      <th className="pb-2 font-medium">Plan</th>
                      <th className="pb-2 font-medium">Price</th>
                      <th className="pb-2 font-medium">Subscribers</th>
                      <th className="pb-2 font-medium">MRR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(overview.plan_breakdown.length ? overview.plan_breakdown : overview.plans.map((p) => ({
                      plan_code: p.code,
                      plan_name: p.name,
                      subscribers: 0,
                      mrr_cents: 0,
                      monthly_price_cents: p.monthly_price_cents,
                    }))).map((row) => (
                      <tr key={row.plan_code} className="border-t border-[var(--line)]">
                        <td className="py-2.5">{row.plan_name}</td>
                        <td className="py-2.5 tabular-nums text-[var(--fg-muted)]">{money(row.monthly_price_cents)}</td>
                        <td className="py-2.5 tabular-nums">{row.subscribers}</td>
                        <td className="py-2.5 tabular-nums">{money(row.mrr_cents)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="glass rounded-2xl p-4">
              <h2 className="text-lg font-medium">Catalog</h2>
              <p className="mt-1 text-xs text-[var(--fg-muted)]">Configured public plans</p>
              <ul className="mt-3 space-y-2">
                {overview.plans.map((plan) => (
                  <li key={plan.code} className="flex items-center justify-between gap-3 rounded-xl border border-[var(--line)] px-3 py-2 text-sm">
                    <div>
                      <div className="font-medium">{plan.name}</div>
                      <div className="text-xs text-[var(--fg-muted)]">{plan.code}{plan.contact_sales ? " · contact sales" : ""}</div>
                    </div>
                    <div className="tabular-nums">{plan.contact_sales ? "Custom" : plan.price.formatted}</div>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="mt-6 grid gap-4 xl:grid-cols-2">
            <div className="glass rounded-2xl p-4">
              <div className="flex items-end justify-between gap-3">
                <div>
                  <h2 className="text-lg font-medium">Transactions</h2>
                  <p className="mt-1 text-xs text-[var(--fg-muted)]">
                    Subscription ledger · volume {overview.transaction_summary.posted_volume.formatted}
                  </p>
                </div>
                <div className="text-xs text-[var(--fg-muted)]">
                  {Object.entries(overview.transaction_summary.providers || {})
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ") || "no providers"}
                </div>
              </div>
              <div className="mt-3 max-h-[420px] overflow-auto">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead className="sticky top-0 bg-[rgba(10,15,28,0.95)] text-xs uppercase tracking-wide text-[var(--fg-muted)]">
                    <tr>
                      <th className="pb-2 pr-2 font-medium">When</th>
                      <th className="pb-2 pr-2 font-medium">Org</th>
                      <th className="pb-2 pr-2 font-medium">Type</th>
                      <th className="pb-2 pr-2 font-medium">Plan</th>
                      <th className="pb-2 font-medium">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.transactions.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-6 text-[var(--fg-muted)]">
                          No billing transactions yet. Activate a plan from a customer tenant to populate the ledger.
                        </td>
                      </tr>
                    ) : (
                      overview.transactions.map((tx) => (
                        <tr key={tx.id} className="border-t border-[var(--line)] align-top">
                          <td className="py-2.5 pr-2 text-xs text-[var(--fg-muted)]">{when(tx.created_at)}</td>
                          <td className="py-2.5 pr-2">{tx.organization_name}</td>
                          <td className="py-2.5 pr-2">
                            <div>{tx.type}</div>
                            <div className="text-xs text-[var(--fg-muted)]">
                              {tx.status} · {tx.provider}
                            </div>
                          </td>
                          <td className="py-2.5 pr-2 text-[var(--fg-muted)]">{tx.plan_name || "—"}</td>
                          <td className="py-2.5 tabular-nums">{tx.amount.formatted}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="glass rounded-2xl p-4">
              <h2 className="text-lg font-medium">Subscriptions</h2>
              <p className="mt-1 text-xs text-[var(--fg-muted)]">Latest tenant subscription rows</p>
              <div className="mt-3 max-h-[420px] overflow-auto">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead className="sticky top-0 bg-[rgba(10,15,28,0.95)] text-xs uppercase tracking-wide text-[var(--fg-muted)]">
                    <tr>
                      <th className="pb-2 pr-2 font-medium">Organization</th>
                      <th className="pb-2 pr-2 font-medium">Plan</th>
                      <th className="pb-2 pr-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">Monthly</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.subscriptions.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-6 text-[var(--fg-muted)]">
                          No subscriptions yet.
                        </td>
                      </tr>
                    ) : (
                      overview.subscriptions.map((sub) => (
                        <tr key={sub.id} className="border-t border-[var(--line)]">
                          <td className="py-2.5 pr-2">
                            <div>{sub.organization_name}</div>
                            <div className="text-xs text-[var(--fg-muted)]">{when(sub.updated_at)}</div>
                          </td>
                          <td className="py-2.5 pr-2 text-[var(--fg-muted)]">{sub.plan_name || "—"}</td>
                          <td className="py-2.5 pr-2">
                            {sub.status}
                            <div className="text-xs text-[var(--fg-muted)]">{sub.provider}</div>
                          </td>
                          <td className="py-2.5 tabular-nums">{money(sub.monthly_price_cents)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section className="mt-6 grid gap-4 xl:grid-cols-2">
            <div className="glass rounded-2xl p-4">
              <h2 className="text-lg font-medium">Organizations</h2>
              <div className="mt-3 max-h-[360px] overflow-auto">
                <table className="w-full min-w-[560px] text-left text-sm">
                  <thead className="sticky top-0 bg-[rgba(10,15,28,0.95)] text-xs uppercase tracking-wide text-[var(--fg-muted)]">
                    <tr>
                      <th className="pb-2 pr-2 font-medium">Name</th>
                      <th className="pb-2 pr-2 font-medium">Members</th>
                      <th className="pb-2 pr-2 font-medium">Devices</th>
                      <th className="pb-2 pr-2 font-medium">Plan</th>
                      <th className="pb-2 font-medium">MRR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.organizations_detail.map((org) => (
                      <tr key={org.id} className="border-t border-[var(--line)]">
                        <td className="py-2.5 pr-2">
                          <div>{org.name}</div>
                          <div className="text-xs text-[var(--fg-muted)]">{org.slug}</div>
                        </td>
                        <td className="py-2.5 pr-2 tabular-nums">{org.members}</td>
                        <td className="py-2.5 pr-2 tabular-nums">{org.devices}</td>
                        <td className="py-2.5 pr-2 text-[var(--fg-muted)]">
                          {org.plan_name || "—"}
                          <div className="text-xs">{org.subscription_status}</div>
                        </td>
                        <td className="py-2.5 tabular-nums">{money(org.mrr_cents)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="glass rounded-2xl p-4">
              <h2 className="text-lg font-medium">Recent users</h2>
              <div className="mt-3 max-h-[360px] overflow-auto">
                <table className="w-full min-w-[480px] text-left text-sm">
                  <thead className="sticky top-0 bg-[rgba(10,15,28,0.95)] text-xs uppercase tracking-wide text-[var(--fg-muted)]">
                    <tr>
                      <th className="pb-2 pr-2 font-medium">Name</th>
                      <th className="pb-2 pr-2 font-medium">Email</th>
                      <th className="pb-2 pr-2 font-medium">Verified</th>
                      <th className="pb-2 font-medium">Joined</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.recent_users.map((u) => (
                      <tr key={u.id} className="border-t border-[var(--line)]">
                        <td className="py-2.5 pr-2">{u.display_name}</td>
                        <td className="py-2.5 pr-2 text-[var(--fg-muted)]">{u.email}</td>
                        <td className="py-2.5 pr-2">
                          {u.email_verified ? "yes" : "no"}
                          {u.mfa_enabled ? " · MFA" : ""}
                        </td>
                        <td className="py-2.5 text-xs text-[var(--fg-muted)]">{when(u.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="glass rounded-2xl p-4">
              <h2 className="text-lg font-medium">Agent builds</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {(overview.agent_versions || []).map((row) => (
                  <li key={`${row.platform}-${row.version}`} className="rounded-xl border border-[var(--line)] px-3 py-2">
                    <div className="font-medium">
                      {row.platform} · v{row.version}
                    </div>
                    <p className="mt-1 text-xs leading-5 text-[var(--fg-muted)]">{row.notes}</p>
                  </li>
                ))}
              </ul>
            </div>
            <div className="glass rounded-2xl p-4">
              <h2 className="text-lg font-medium">System incidents</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {(overview.system_incidents || []).length === 0 ? (
                  <li className="text-[var(--fg-muted)]">No platform incidents recorded.</li>
                ) : (
                  (overview.system_incidents || []).map((row) => (
                    <li key={row.id} className="rounded-xl border border-[var(--line)] px-3 py-2">
                      <div className="font-medium">{row.title}</div>
                      <div className="mt-1 text-xs text-[var(--fg-muted)]">
                        {row.severity} · {row.status} · {when(row.created_at)}
                      </div>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </section>
        </>
      ) : null}

      <section className="glass mt-6 rounded-2xl p-4">
        <h2 className="text-lg font-medium">Recent audit</h2>
        <div className="mt-3 max-h-[320px] overflow-auto">
          <ul className="space-y-1.5 font-mono text-xs text-[var(--fg-muted)]">
            {audit.map((row) => (
              <li key={row.id} className="border-b border-[var(--line)] py-1.5 last:border-0">
                {when(row.created_at)} · {row.actor_type} · {row.action}
                {row.resource_type ? ` · ${row.resource_type}` : ""}
              </li>
            ))}
          </ul>
        </div>
        {overview?.note ? <p className="mt-4 text-xs text-[var(--fg-muted)]">{overview.note}</p> : null}
      </section>
    </main>
  );
}
