export type Severity = "informational" | "low" | "medium" | "high" | "critical";

export function severityColor(value: string) {
  const map: Record<string, string> = {
    informational: "var(--fg-muted)",
    low: "var(--ai)",
    medium: "var(--warning)",
    high: "var(--high)",
    critical: "var(--critical)",
  };
  return map[value] || "var(--fg-muted)";
}

export const nav = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/devices", label: "Devices" },
  { href: "/dashboard/alerts", label: "Alerts" },
  { href: "/dashboard/incidents", label: "Incidents" },
  { href: "/dashboard/vulnerabilities", label: "Vulnerabilities" },
  { href: "/dashboard/ai", label: "AI Security Team" },
  { href: "/dashboard/reports", label: "Reports" },
  { href: "/dashboard/subscription", label: "Subscription" },
  { href: "/dashboard/settings", label: "Settings" },
];

export const publicNav = [
  { href: "/platform", label: "Platform" },
  { href: "/endpoint-security", label: "Endpoint" },
  { href: "/ai-security", label: "AI Security" },
  { href: "/pricing", label: "Pricing" },
  { href: "/enterprise", label: "Enterprise" },
  { href: "/docs", label: "Docs" },
  { href: "/security", label: "Security" },
];
