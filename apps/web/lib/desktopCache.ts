/** Lightweight desktop cache helpers for $APPDATA/orqelis/cache.json (via Tauri fs). */

export type DesktopCache = {
  updated_at: string;
  dashboard?: unknown;
  devices?: unknown;
  web_assets?: unknown;
};

const KEY = "orqelis_desktop_cache";

export function readDesktopCache(): DesktopCache | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as DesktopCache) : null;
  } catch {
    return null;
  }
}

export function writeDesktopCache(partial: Partial<DesktopCache>) {
  if (typeof window === "undefined") return;
  const prev = readDesktopCache() || { updated_at: new Date().toISOString() };
  const next: DesktopCache = {
    ...prev,
    ...partial,
    updated_at: new Date().toISOString(),
  };
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* ignore quota */
  }
}
