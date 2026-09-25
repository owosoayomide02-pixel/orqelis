import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="AI Security"
      kicker="ASSIST, DON’T OVERRIDE"
      lead="Orqelis uses an internal AI gateway so provider keys never reach browsers or endpoint agents. AI explains alerts, summarizes incidents, and recommends defensive remediation — it does not autonomously perform high-impact actions."
      aside={
        <>
          <ContentCard title="Detection stays rule-based">
            <p>An LLM is never the only detector. Correlated findings come from the dedicated detection package first.</p>
          </ContentCard>
          <ContentCard title="Human in the loop">
            <p>Recommended actions appear in the dashboard. An authorized operator must approve before supported agent actions run.</p>
          </ContentCard>
          <ContentCard title="Related">
            <div className="flex flex-col gap-1.5">
              <Link href="/platform">Platform overview →</Link>
              <Link href="/security">Security page →</Link>
              <Link href="/docs">Documentation →</Link>
            </div>
          </ContentCard>
        </>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Explain alerts",
            body: "Translate technical detections into operator-readable narratives with likely impact and context.",
          },
          {
            title: "Summarize incidents",
            body: "Collapse correlated events into a timeline-oriented summary for triage and handoff.",
          },
          {
            title: "Recommend remediation",
            body: "Suggest defensive next steps aligned to supported actions — never invent remote shell capabilities.",
          },
          {
            title: "Gateway isolation",
            body: "Browser and agent clients talk to Orqelis APIs only. Provider credentials stay server-side.",
          },
        ]}
      />
      <ContentCard title="Failure mode">
        <p>
          If the AI provider is unavailable, the product continues with heuristic fallbacks where configured. Detection and
          enrollment do not depend on generative AI being online.
        </p>
      </ContentCard>
    </Marketing>
  );
}
