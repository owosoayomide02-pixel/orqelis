export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function isDesktop(): boolean {
  return typeof window !== "undefined" && "__TAURI__" in window;
}

function desktopAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem("orqelis_access_token");
  } catch {
    return null;
  }
}

function apiBase(): string {
  const env = (typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_URL : "") || "";
  const staticExport = typeof process !== "undefined" && process.env.NEXT_PUBLIC_STATIC_EXPORT === "1";
  if (isDesktop() || staticExport) return env.replace(/\/$/, "");
  return "";
}

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (isDesktop()) {
    const token = desktopAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const base = apiBase();
  const response = await fetch(`${base}${path}`, {
    ...init,
    credentials: isDesktop() ? "omit" : "include",
    headers,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail))
        detail = body.detail.map((item: { msg?: string }) => item.msg || JSON.stringify(item)).join("; ");
      else if (body.detail) detail = JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(response.status, typeof detail === "string" ? detail : "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function apiUrl() {
  return apiBase();
}

export type WebAsset = {
  id: string;
  domain: string;
  verification_status: string;
  verification_method?: string;
  verified_at?: string | null;
  created_at?: string | null;
  archived?: boolean;
  verification_instructions?: {
    record_type: string;
    record_name: string;
    record_value: string;
  };
  message?: string;
};

export type ScanJob = {
  id: string;
  status: string;
  tools_run: string[];
  current_tool?: string | null;
  findings_count: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
};

export type Finding = {
  id: string;
  source?: string;
  source_id?: string;
  title: string;
  severity: string;
  confidence?: number;
  risk_score?: number;
  detection_source?: string;
  evidence?: Record<string, unknown>;
  recommended_next_step?: string;
  status?: string;
  auto_detected?: boolean;
  created_at?: string | null;
};

export type AnalystResult = {
  explanation: string;
  severity_assessment: string;
  confidence: number;
  analysis_id?: string;
  auto_detected?: boolean;
};

export type FixerResult = {
  fix_type: string;
  description: string;
  diff: string;
  requires_human_approval: boolean;
  analysis_id?: string;
  applied?: boolean;
};

export async function listWebAssets() {
  return api<WebAsset[]>("/api/v1/web-assets");
}

export async function createWebAsset(domain: string) {
  return api<WebAsset>("/api/v1/web-assets", { method: "POST", body: JSON.stringify({ domain }) });
}

export async function getWebAsset(id: string) {
  return api<WebAsset>(`/api/v1/web-assets/${id}`);
}

export async function verifyWebAsset(id: string, testMode = false) {
  const headers: HeadersInit = {};
  if (testMode) headers["X-Orqelis-Test-Verify"] = "1";
  return api<WebAsset>(`/api/v1/web-assets/${id}/verify`, { method: "POST", headers });
}

export async function startScan(id: string, role: "hunter" = "hunter") {
  return api<{ scan_job_id: string; status: string }>(`/api/v1/web-assets/${id}/scan`, {
    method: "POST",
    body: JSON.stringify({ role }),
  });
}

export async function getScanStatus(webAssetId: string, scanJobId: string) {
  return api<ScanJob>(`/api/v1/web-assets/${webAssetId}/scans/${scanJobId}`);
}

export async function listScans(webAssetId: string) {
  return api<ScanJob[]>(`/api/v1/web-assets/${webAssetId}/scans`);
}

export async function getFindings(webAssetId: string) {
  return api<Finding[]>(`/api/v1/web-assets/${webAssetId}/findings`);
}

export async function analyzeFinding(findingId: string) {
  return api<AnalystResult>(`/api/v1/findings/${findingId}/analyze`, { method: "POST", body: "{}" });
}

export async function fixFinding(findingId: string) {
  return api<FixerResult>(`/api/v1/findings/${findingId}/fix`, { method: "POST", body: "{}" });
}

export async function generateReport(webAssetId: string) {
  return api<{ report_job_id: string; status: string; report_id?: string }>(
    `/api/v1/web-assets/${webAssetId}/report`,
    { method: "POST", body: "{}" },
  );
}

export async function getReport(webAssetId: string, reportId: string) {
  return api<{ id: string; title: string; body_markdown: string; status: string }>(
    `/api/v1/web-assets/${webAssetId}/report/${reportId}`,
  );
}

export async function desktopLogin(email: string, password: string, totp = "") {
  return api<{
    access_token: string;
    refresh_token: string;
    mfa_required?: boolean;
  }>("/api/v1/auth/desktop-login", {
    method: "POST",
    body: JSON.stringify({ email, password, totp }),
  });
}
