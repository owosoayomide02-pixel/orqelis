"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/DashboardShell";
import { api } from "@/lib/api";

type Device = {
  id: string;
  name: string;
  hostname: string;
  os_name: string;
  status: string;
  agent_version: string;
  last_seen_at: string | null;
};

type Download = {
  platform: string;
  label: string;
  version: string;
  notes: string;
  binary_available: boolean;
  download_path: string | null;
  package_command: string;
  enroll_commands: string;
  notice: string;
};

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [downloads, setDownloads] = useState<Download[]>([]);
  const [downloadNotice, setDownloadNotice] = useState("");
  const [devicesReady, setDevicesReady] = useState(false);
  const [devicesFailed, setDevicesFailed] = useState(false);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  async function loadDevices() {
    const rows = await api<Device[]>("/api/v1/devices");
    setDevices(rows);
    setDevicesFailed(false);
  }

  async function loadDownloads() {
    const pack = await api<{ notice: string; platforms: Download[] }>("/api/v1/devices/agent-downloads");
    setDownloads(pack.platforms);
    setDownloadNotice(pack.notice);
  }

  useEffect(() => {
    loadDevices()
      .catch((err) => {
        setDevicesFailed(true);
        setError(err instanceof Error ? err.message : "Could not load devices");
      })
      .finally(() => setDevicesReady(true));
    loadDownloads().catch((err) => {
      setError(err instanceof Error ? err.message : "Could not load installer commands");
    });
  }, []);

  async function enroll() {
    setError("");
    try {
      const result = await api<{ code: string }>("/api/v1/devices/enrollments", { method: "POST", body: JSON.stringify({}) });
      setCode(result.code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create enrollment");
      return;
    }
    try {
      await Promise.all([loadDevices(), loadDownloads()]);
    } catch {
      setError("Enrollment created, but the device list could not be refreshed.");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold">Devices</h1>
        <button className="btn btn-primary" onClick={enroll}>
          Create enrollment code
        </button>
      </div>
      {code ? (
        <div className="glass mt-6 rounded-3xl p-5">
          <div className="text-sm text-[var(--fg-muted)]">One-time code · Windows, macOS, or Linux</div>
          <div className="mt-2 text-3xl tracking-[0.4em]">{code}</div>
          <p className="mt-3 text-sm text-[var(--fg-muted)]">Use the enroll command for your OS below. The API URL is taken from the server config, not localhost.</p>
        </div>
      ) : null}
      {error ? (
        <p className="mt-4 text-[var(--critical)]" role="alert">
          {error}
        </p>
      ) : null}
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {downloads.map((item) => (
          <div key={item.platform} className="glass rounded-3xl p-5">
            <div className="text-lg">{item.label}</div>
            <div className="mt-1 text-xs uppercase tracking-wide text-[var(--fg-muted)]">agent {item.version}</div>
            <p className="mt-3 text-sm text-[var(--fg-muted)]">{item.notes || item.notice}</p>
            {item.binary_available && item.download_path ? (
              <a className="btn btn-primary mt-4 w-full" href={item.download_path}>
                Download
              </a>
            ) : (
              <p className="mt-4 text-sm text-[var(--fg-muted)]">
                No packaged binary on this machine. Run <code>{item.package_command}</code> or enroll with Python:
              </p>
            )}
            <pre className="mt-3 overflow-x-auto text-xs text-[var(--fg-muted)]">{item.enroll_commands.replace("YOURCODE", code || "YOURCODE")}</pre>
          </div>
        ))}
      </div>
      {downloadNotice ? <p className="mt-3 text-xs text-[var(--fg-muted)]">{downloadNotice}</p> : null}
      <div className="mt-8 space-y-3">
        {!devicesReady ? (
          <p className="text-[var(--fg-muted)]">Loading devices…</p>
        ) : devicesFailed ? (
          <EmptyState title="Devices unavailable" body="The device list could not be loaded. Check that the API is running, then refresh." />
        ) : devices.length === 0 ? (
          <EmptyState title="No enrolled devices" body="Install the Orqelis agent on Windows, macOS, or Linux computers you are authorized to manage." />
        ) : (
          devices.map((device) => (
            <Link key={device.id} href={`/dashboard/devices/${device.id}`} className="glass flex items-center justify-between rounded-3xl p-5">
              <div>
                <div className="text-lg">{device.hostname || device.name}</div>
                <div className="text-sm text-[var(--fg-muted)]">
                  {device.os_name} · agent {device.agent_version} · {device.last_seen_at || "never seen"}
                </div>
              </div>
              <div className="text-sm uppercase tracking-wide text-[var(--ai)]">{device.status}</div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
