import { Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing title="Pricing" kicker="CONFIGURATION-DRIVEN">
      <p>Proposed starting plans. Production billing is not live in v0.1.0.</p>
      <ul className="list-disc pl-5">
        <li>Personal — $20 / month</li>
        <li>Business Core — from $500 / month</li>
        <li>Enterprise — contact sales</li>
      </ul>
    </Marketing>
  );
}
