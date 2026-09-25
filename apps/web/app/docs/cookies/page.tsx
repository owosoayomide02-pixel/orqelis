import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Cookie Policy"
      kicker="LEGAL DRAFT"
      lead="Essential cookies are used for authentication and security. Analytics or marketing cookies are not enabled by default in v0.1.0."
      aside={
        <ContentCard title="Related">
          <div className="flex flex-col gap-1.5">
            <Link href="/docs/privacy">Privacy Policy →</Link>
            <Link href="/docs/terms">Terms of Service →</Link>
          </div>
        </ContentCard>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Session cookies",
            body: "Keep you signed in to the customer dashboard after login. Required for authenticated API calls from the browser.",
          },
          {
            title: "Security cookies",
            body: "Help protect authentication flows (for example CSRF or session integrity controls where configured).",
          },
          {
            title: "Preferences",
            body: "May store lightweight UI preferences such as dismissed banners. Not used for third-party advertising in this release.",
          },
          {
            title: "Not enabled by default",
            body: "Product analytics and marketing trackers are off unless explicitly introduced in a later release with updated notices.",
          },
        ]}
      />
      <ContentCard title="Managing cookies">
        <p>You can clear site data in your browser. Signing out ends the Orqelis session cookie for this application.</p>
      </ContentCard>
    </Marketing>
  );
}
