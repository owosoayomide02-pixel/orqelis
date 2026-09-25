"use client";

const ROLES = [
  { id: "sentinel", label: "Sentinel", blurb: "Passive monitoring — auto-triages high/critical" },
  { id: "hunter", label: "Hunter", blurb: "Active recon — subfinder, httpx, nmap, nuclei" },
  { id: "analyst", label: "Analyst", blurb: "Explain a finding in plain language" },
  { id: "auditor", label: "Auditor", blurb: "Client-facing report" },
  { id: "fixer", label: "Fixer", blurb: "Draft remediation — never auto-applies" },
] as const;

export function RoleSelector({
  verified,
  active,
  onSelect,
  disabled,
}: {
  verified: boolean;
  active?: string;
  onSelect: (role: (typeof ROLES)[number]["id"]) => void;
  disabled?: boolean;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {ROLES.map((role) => {
        const locked = role.id !== "sentinel" && !verified;
        const isActive = active === role.id;
        return (
          <button
            key={role.id}
            type="button"
            disabled={locked || disabled}
            onClick={() => onSelect(role.id)}
            className={`rounded-2xl border p-4 text-left transition ${
              isActive ? "border-[var(--accent)] bg-[var(--surface-2)]" : "border-[var(--line)] bg-[var(--surface)]"
            } ${locked ? "opacity-40" : "hover:border-[var(--accent)]"}`}
          >
            <div className="text-sm font-medium">{role.label}</div>
            <p className="mt-1 text-xs text-[var(--fg-muted)]">{role.blurb}</p>
            {locked ? <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--warning)]">Verify domain first</p> : null}
          </button>
        );
      })}
    </div>
  );
}
