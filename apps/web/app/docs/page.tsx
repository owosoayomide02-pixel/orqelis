import { Marketing } from "@/components/SiteChrome";
import Link from "next/link";

export default function Page() {
  return (
    <Marketing title="Documentation" kicker="PUBLIC">
      <ul className="space-y-2">
        <li><Link href="/docs/privacy">Privacy Policy</Link></li>
        <li><Link href="/docs/terms">Terms of Service</Link></li>
        <li><Link href="/security">Security</Link></li>
        <li><Link href="/docs/disclosure">Vulnerability Disclosure</Link></li>
      </ul>
      <p>Full product and customer guides are in the repository docs directory.</p>
    </Marketing>
  );
}
