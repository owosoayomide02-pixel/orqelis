import { Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing title="Developers" kicker="API V1">
      <p>Human APIs use session cookies. Agent APIs use a device token header. They are not interchangeable.</p>
      <p>
        Versioned routes live under <code>/api/v1/</code>. See customer and developer documentation in this repository’s
        docs folder.
      </p>
    </Marketing>
  );
}
