"use client";

import { useEffect, useState } from "react";

/**
 * Desktop offline banner — polls API /health when running inside Tauri.
 */
export function OfflineBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const isDesktop = typeof window !== "undefined" && "__TAURI__" in window;
    if (!isDesktop) return;
    const base = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
    if (!base) return;

    let cancelled = false;
    async function ping() {
      try {
        const res = await fetch(`${base}/health`, { cache: "no-store" });
        if (!cancelled) setOffline(!res.ok);
      } catch {
        if (!cancelled) setOffline(true);
      }
    }
    ping();
    const id = window.setInterval(ping, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  if (!offline) return null;
  return (
    <div className="border-b border-[var(--warning)] bg-[var(--bg-warning)] px-4 py-2 text-center text-sm text-[var(--text-warning)]">
      Offline — showing cached data. Network actions are disabled until the API is reachable.
    </div>
  );
}
