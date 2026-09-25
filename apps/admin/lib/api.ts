const API = "";

let supabaseAccessToken: string | null = null;

export function setSupabaseAccessToken(token: string | null) {
  supabaseAccessToken = token;
  if (typeof window !== "undefined") {
    if (token) window.sessionStorage.setItem("orqelis_supabase_access", token);
    else window.sessionStorage.removeItem("orqelis_supabase_access");
  }
}

function bearer(): string | null {
  if (supabaseAccessToken) return supabaseAccessToken;
  if (typeof window !== "undefined") {
    return window.sessionStorage.getItem("orqelis_supabase_access");
  }
  return null;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = bearer();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API}${path}`, { ...init, credentials: "include", headers });
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
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return response.json();
}
