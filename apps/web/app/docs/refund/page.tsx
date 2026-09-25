import Link from "next/link";
import { ContentCard, DetailGrid, Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing
      title="Refund Policy"
      kicker="LEGAL DRAFT"
      lead="Monthly subscriptions may be canceled for future renewals. Automatic refunds are not promised until a live payment provider and legal policy are finalized."
      aside={
        <ContentCard title="Billing today">
          <p>v0.1.0 uses a development billing provider only. Live Stripe/Paystack charging is not enabled.</p>
          <Link href="/pricing" className="mt-3 inline-block text-[var(--brand)]">
            Pricing plans →
          </Link>
        </ContentCard>
      }
    >
      <DetailGrid
        items={[
          {
            title: "Cancellation",
            body: "You may cancel to stop future renewals. Access continues through the end of the paid period once live billing exists.",
          },
          {
            title: "Refunds",
            body: "Automatic prorated refunds are not guaranteed in this draft. Enterprise contracts may define separate commercial terms.",
          },
          {
            title: "Disputes",
            body: "Contact [SUPPORT EMAIL] or [LEGAL EMAIL] with invoice identifiers and a short description of the issue.",
          },
          {
            title: "Early release note",
            body: "Until production billing ships, treat published prices as planning figures rather than charged amounts.",
          },
        ]}
      />
    </Marketing>
  );
}
