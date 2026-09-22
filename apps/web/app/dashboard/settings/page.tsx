"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Me = {
  email: string;
  display_name: string;
  email_verified: boolean;
  mfa_enabled: boolean;
  dev_email_links?: boolean;
  organizations: { name: string; role: string }[];
};
type Session = { id: string; user_agent: string; ip_address: string; created_at: string; revoked: boolean };
type Approval = { id: string; title: string; reason: string; risk_class: string; status: string };

export default function SettingsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [mfaSecret, setMfaSecret] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaPassword, setMfaPassword] = useState("");
  const [mfaMessage, setMfaMessage] = useState("");

  async function load() {
    const [a, b, c] = await Promise.all([
      api<Me>("/api/v1/auth/me"),
      api<Session[]>("/api/v1/auth/sessions"),
      api<Approval[]>("/api/v1/approvals"),
    ]);
    setMe(a);
    setSessions(b);
    setApprovals(c);
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  return (
    <div>
      <h1 className="text-3xl font-semibold">Settings</h1>
      {me ? (
        <div className="glass mt-6 rounded-3xl p-6">
          <div>{me.display_name}</div>
          <div className="text-sm text-[var(--fg-muted)]">
            {me.email} · {me.organizations[0]?.role} · email {me.email_verified ? "verified" : "pending"} · MFA {me.mfa_enabled ? "on" : "off"}
          </div>
          {!me.email_verified && me.dev_email_links ? (
            <button
              className="btn btn-primary mt-4 !py-2"
              onClick={async () => {
                const result = await api<{ verification_url?: string }>("/api/v1/auth/verification-link", { method: "POST" });
                if (result.verification_url) window.location.href = result.verification_url;
              }}
            >
              Open verification link
            </button>
          ) : null}
        </div>
      ) : null}
      <h2 className="mt-10 text-xl">Authenticator (TOTP)</h2>
      <p className="mt-2 text-sm text-[var(--fg-muted)]">Optional second factor. Store the secret in an authenticator app. This is not SMS.</p>
      {me && !me.mfa_enabled ? (
        <div className="glass mt-4 rounded-3xl p-6">
          <button
            className="btn btn-primary !py-2"
            onClick={async () => {
              const setup = await api<{ secret: string; otpauth_url: string }>("/api/v1/auth/mfa/setup", { method: "POST" });
              setMfaSecret(setup.secret);
              setMfaMessage(setup.otpauth_url);
            }}
          >
            Generate secret
          </button>
          {mfaSecret ? <p className="mt-3 break-all text-sm">Secret: {mfaSecret}</p> : null}
          {mfaMessage ? <p className="mt-2 break-all text-xs text-[var(--fg-muted)]">{mfaMessage}</p> : null}
          <input className="mt-3" placeholder="6-digit code" value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} />
          <button
            className="btn btn-primary mt-3 !py-2"
            onClick={async () => {
              await api("/api/v1/auth/mfa/enable", { method: "POST", body: JSON.stringify({ code: mfaCode }) });
              setMfaCode("");
              await load();
            }}
          >
            Enable MFA
          </button>
        </div>
      ) : me?.mfa_enabled ? (
        <div className="glass mt-4 rounded-3xl p-6">
          <p className="text-sm text-[var(--success)]">Authenticator is on.</p>
          <input className="mt-3" type="password" placeholder="Password" value={mfaPassword} onChange={(e) => setMfaPassword(e.target.value)} />
          <input className="mt-3" placeholder="6-digit code" value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} />
          <button
            className="btn btn-ghost mt-3 !py-2"
            onClick={async () => {
              await api("/api/v1/auth/mfa/disable", { method: "POST", body: JSON.stringify({ password: mfaPassword, code: mfaCode }) });
              setMfaCode("");
              setMfaPassword("");
              await load();
            }}
          >
            Disable MFA
          </button>
        </div>
      ) : null}
      <h2 className="mt-10 text-xl">Sessions</h2>
      <div className="mt-4 space-y-2">
        {sessions.map((session) => (
          <div key={session.id} className="glass flex items-center justify-between rounded-2xl p-4 text-sm">
            <span className="text-[var(--fg-muted)]">
              {session.ip_address} · {session.user_agent.slice(0, 80)} {session.revoked ? "· revoked" : ""}
            </span>
            {!session.revoked ? (
              <button
                onClick={async () => {
                  await api(`/api/v1/auth/sessions/${session.id}/revoke`, { method: "POST" });
                  await load();
                }}
              >
                Revoke
              </button>
            ) : null}
          </div>
        ))}
      </div>
      <h2 className="mt-10 text-xl">Approvals</h2>
      <p className="mt-2 text-sm text-[var(--fg-muted)]">V1 supported actions: refresh agent policy, restart the Orqelis agent only.</p>
      <div className="mt-4 space-y-2">
        {approvals.map((row) => (
          <div key={row.id} className="glass flex items-center justify-between rounded-2xl p-4">
            <div>
              <div>{row.title}</div>
              <div className="text-sm text-[var(--fg-muted)]">
                {row.risk_class} · {row.status} · {row.reason}
              </div>
            </div>
            {row.status === "pending" ? (
              <button
                className="btn btn-primary !py-2"
                onClick={async () => {
                  await api(`/api/v1/approvals/${row.id}/decide`, { method: "POST", body: JSON.stringify({ decision: "approve" }) });
                  await load();
                }}
              >
                Approve
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
