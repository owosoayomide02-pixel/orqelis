import { Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing title="AI Security" kicker="ASSIST, DON’T OVERRIDE">
      <p>
        Orqelis uses an internal AI gateway so provider keys never reach browsers or endpoint agents. AI explains alerts,
        summarizes incidents, and recommends defensive remediation.
      </p>
      <p>Detection itself is rule-based. AI does not autonomously perform high-impact actions.</p>
    </Marketing>
  );
}
