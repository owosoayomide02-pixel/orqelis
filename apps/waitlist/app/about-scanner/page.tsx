import Link from "next/link";

export const metadata = {
  title: "About our scanner | Orqelis",
  description: "Learn about Orqelis scanner scope, safety, and how to report suspected abuse.",
};

export default function AboutScannerPage() {
  return (
    <main className="policy-page">
      <header className="policy-header">
        <Link href="/" className="policy-brand">ORQELIS · EARLY ACCESS</Link>
        <Link href="/" className="policy-back">Back to waitlist</Link>
      </header>
      <article className="policy-content">
        <p className="eyebrow">SCOPE · SAFETY · ACCOUNTABILITY</p>
        <h1>About our scanner</h1>
        <p className="policy-notice">
          Orqelis is in development. The controls described here are the intended V1 design, not a claim that
          scanning is currently available.
        </p>
        <p className="policy-intro">
          Orqelis is being built to help teams understand the security of their public web assets without
          scanning systems they do not own or have permission to assess.
        </p>
        <section className="policy-section">
          <h2>Verified scope only</h2>
          <p>
            Before a scan can run, a customer must prove control of the domain. Discovery and checks are intended
            to remain within that verified scope. Do not use Orqelis to assess a domain or service without
            authorization.
          </p>
        </section>
        <section className="policy-section">
          <h2>Read-only checks</h2>
          <p>
            The V1 scanner is planned for passive, read-only checks such as reviewing TLS configuration, security
            headers, and publicly observable API exposure. It is not intended to exploit vulnerabilities, change
            application data, or modify target systems.
          </p>
        </section>
        <section className="policy-section">
          <h2>Report suspected abuse</h2>
          <p>
            If you believe an Orqelis scan has touched a domain without authorization, email{" "}
            <a href="mailto:support@waitlist.orqelis.dev">support@waitlist.orqelis.dev</a> with the affected
            domain, approximate time, and any relevant request details. Do not include passwords, tokens, or
            other secrets.
          </p>
        </section>
        <section className="policy-section">
          <h2>Questions about your data</h2>
          <p>
            For privacy questions about waitlist information, see the{" "}
            <Link href="/privacy">Waitlist Privacy Policy</Link>.
          </p>
        </section>
      </article>
      <footer className="policy-footer">
        <span>© {new Date().getFullYear()} Orqelis</span>
        <Link href="/">Return to the waitlist</Link>
      </footer>
    </main>
  );
}
