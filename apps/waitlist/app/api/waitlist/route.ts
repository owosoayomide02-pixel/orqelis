import { NextResponse } from "next/server";

type WaitlistPayload = {
  email?: unknown;
  website?: unknown;
};

function apiEndpoint(): URL {
  const configured = process.env.WAITLIST_API_URL?.trim();
  const base = configured || "https://orqelis-api-production.up.railway.app";
  const url = new URL(base);
  if (url.protocol !== "https:" && url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
    throw new Error("WAITLIST_API_URL must use HTTPS outside local development.");
  }
  url.pathname = `${url.pathname.replace(/\/+$/, "")}/api/v1/waitlist`;
  url.search = "";
  url.hash = "";
  return url;
}

export async function POST(request: Request) {
  let payload: WaitlistPayload;
  try {
    payload = (await request.json()) as WaitlistPayload;
  } catch {
    return NextResponse.json({ error: "Enter a valid email address." }, { status: 400 });
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return NextResponse.json({ error: "Enter a valid email address." }, { status: 400 });
  }

  try {
    const upstream = await fetch(apiEndpoint(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: typeof payload.email === "string" ? payload.email : "",
        website: typeof payload.website === "string" ? payload.website : "",
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    const body = (await upstream.json().catch(() => ({}))) as {
      received?: boolean;
      detail?: string;
    };
    if (!upstream.ok) {
      return NextResponse.json(
        {
          error:
            (typeof body.detail === "string" && body.detail) ||
            "We couldn't submit your request. Please try again.",
        },
        { status: upstream.status },
      );
    }
    return NextResponse.json({ received: body.received === true });
  } catch {
    return NextResponse.json(
      { error: "The waitlist is temporarily unavailable. Please try again later." },
      { status: 502 },
    );
  }
}
