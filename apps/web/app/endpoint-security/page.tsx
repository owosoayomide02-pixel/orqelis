import { Marketing } from "@/components/SiteChrome";

export default function Page() {
  return (
    <Marketing title="Endpoint Security" kicker="WINDOWS · MACOS · LINUX">
      <p>
        The Orqelis agent collects device, process, authentication, service, network metadata, and security-control status
        on Windows, macOS, and Linux. It does not execute arbitrary remote commands and does not read personal files.
      </p>
      <p>Install it only on computers you own or are authorized to manage. Platform collectors differ: Windows Security log and Defender; macOS Gatekeeper and application firewall; Linux auth logs and host firewall.</p>
    </Marketing>
  );
}
