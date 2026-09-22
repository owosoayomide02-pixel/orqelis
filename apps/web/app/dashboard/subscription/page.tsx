"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Plan = { code: string; name: string; description: string; monthly_price_cents: number; contact_sales: boolean; features: string[] };
type Sub = { status: string; provider: string | null; plan: Plan | null };

export default function SubscriptionPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sub, setSub] = useState<Sub | null>(null);
  const [message, setMessage] = useState("");

  async function load() {
    const [p, s] = await Promise.all([api<Plan[]>("/api/v1/subscription/plans"), api<Sub>("/api/v1/subscription")]);
    setPlans(p);
    setSub(s);
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  return (
    <div>
      <h1 className="text-3xl font-semibold">Subscription</h1>
      <p className="mt-2 text-[var(--fg-muted)]">
        Plans are stored in the database. Live payment charging is not configured. Development activation records a subscription without taking payment.
      </p>
      <p className="mt-4 text-sm">Current status: {sub?.status || "none"} {sub?.plan ? `· ${sub.plan.name}` : ""}</p>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {plans.map((plan) => (
          <div key={plan.code} className="glass rounded-3xl p-6">
            <div className="text-xl">{plan.name}</div>
            <p className="mt-2 text-sm text-[var(--fg-muted)]">{plan.description}</p>
            <div className="mt-4 text-2xl">
              {plan.contact_sales ? "Contact sales" : `$${(plan.monthly_price_cents / 100).toFixed(0)}/mo`}
            </div>
            <ul className="mt-4 space-y-1 text-sm text-[var(--fg-muted)]">
              {plan.features.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            {!plan.contact_sales ? (
              <button
                className="btn btn-primary mt-6 w-full"
                onClick={async () => {
                  try {
                    await api("/api/v1/subscription/activate", { method: "POST", body: JSON.stringify({ plan_code: plan.code }) });
                    setMessage("Development subscription recorded. No charge was made.");
                    await load();
                  } catch (err) {
                    setMessage(err instanceof Error ? err.message : "Could not activate");
                  }
                }}
              >
                Activate (dev)
              </button>
            ) : null}
          </div>
        ))}
      </div>
      {message ? <p className="mt-6 text-sm text-[var(--ai)]">{message}</p> : null}
    </div>
  );
}
