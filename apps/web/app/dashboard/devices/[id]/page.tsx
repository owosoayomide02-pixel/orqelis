"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, Severity } from "@/components/DashboardShell";
import { PostureList } from "@/components/SecurityWidgets";
import { api } from "@/lib/api";

type Detail = {
  id: string;
  hostname: string;
  name: string;
  os_name: string;
  os_version: string;
  agent_version: string;
  status: string;
  last_seen_at: string | null;
  posture_checklist: { id: string; label: string; ok: boolean; detail: string; skip?: boolean }[];
  open_high_alerts: { id: string; title: string; severity: string }[];
  recent_events: { id: string; category: string; event_type: string; occurred_at: string | null }[];
};

export default function DeviceDetailPage() {
  const params = useParams<{ id: string }>();
  const [row, setRow] = useState<Detail | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    api<Detail>(`/api/v1/devices/${params.id}`).then(setRow).catch(() => setRow(null));
  }, [params.id]);
  if (!row) return <EmptyState title="Device" body="This device is not in your organization." />;
  return (
    <div>
      <Link href="/dashboard/devices" className="text-sm text-[var(--fg-muted)]">
        ← Devices
      </Link>
      <h1 className="mt-4 text-3xl font-semibold">{row.hostname || row.name}</h1>
      <p className="mt-2 text-[var(--fg-muted)]">
        {row.os_name} {row.os_version} · agent {row.agent_version} · {row.status} · {row.last_seen_at || "never seen"}
      </p>
      <h2 className="mt-8 text-xl">Posture</h2>
      <div className="mt-4">
        <PostureList items={row.posture_checklist || []} />
      </div>
      <button
        className="btn btn-ghost mt-6"
        onClick={async () => {
          await api("/api/v1/actions/recommend", {
            method: "POST",
            body: JSON.stringify({ device_id: row.id, kind: "refresh_policy", reason: "Refresh collection policy" }),
          });
          setMessage("Policy refresh recommended. Approve it under Settings.");
        }}
      >
        Recommend policy refresh
      </button>
      {message ? <p className="mt-3 text-sm text-[var(--ai)]">{message}</p> : null}
      <h2 className="mt-10 text-xl">Open high-impact alerts</h2>
      <div className="mt-4 space-y-2">
        {row.open_high_alerts?.length ? (
          row.open_high_alerts.map((alert) => (
            <Link key={alert.id} href={`/dashboard/alerts/${alert.id}`} className="glass flex justify-between rounded-2xl p-4">
              <span>{alert.title}</span>
              <Severity value={alert.severity} />
            </Link>
          ))
        ) : (
          <p className="text-sm text-[var(--fg-muted)]">None.</p>
        )}
      </div>
      <h2 className="mt-10 text-xl">Recent telemetry</h2>
      <div className="mt-4 space-y-2">
        {(row.recent_events || []).map((event) => (
          <div key={event.id} className="text-sm text-[var(--fg-muted)]">
            {event.occurred_at} · {event.category} · {event.event_type}
          </div>
        ))}
      </div>
    </div>
  );
}
