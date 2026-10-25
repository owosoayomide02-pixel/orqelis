"use client";

import { FormEvent, useState } from "react";

type FormStatus = "idle" | "submitting" | "success" | "error";

const features = [
  "Verified domains: scans run only on domains you've proven you control",
  "Subdomain and web-asset discovery",
  "TLS and security header checks",
  "Passive API exposure checks",
  "Findings ranked by what to fix first, with plain-English steps",
  "Health bars and score trends",
  "Ignore rules that stick",
  "Weekly rescans, email alerts, and a one-page report",
];

const plans = [
  { name: "Free", price: "$0", scans: "3 scans / month", assets: "1 asset" },
  { name: "Solo", price: "$9", scans: "10 scans / month", assets: "3 assets" },
  { name: "Starter", price: "$19", scans: "25 scans / month", assets: "5 assets", featured: true },
  { name: "Pro", price: "$49", scans: "100 scans / month", assets: "15 assets" },
  { name: "Agency", price: "$129", scans: "Unlimited scans", assets: "25 assets" },
  { name: "Enterprise", price: "Custom", scans: "Unlimited scans", assets: "Custom scope" },
];

const comparisons = [
  {
    name: "Orqelis",
    href: "#pricing",
    pricing: "$0–$129 / month proposed; Enterprise custom",
    note: "Indicative plans for verified-domain monitoring; billing is not live.",
  },
  {
    name: "Detectify",
    href: "https://detectify.com/pricing",
    pricing: "Base price not shown on the public page reviewed",
    note: "The page notes additional per-domain / per-target costs, €500/year for PCI ASV, and €2,500 for five hours of onboarding.",
  },
  {
    name: "Intruder",
    href: "https://www.intruder.io/pricing",
    pricing: "Plan prices not shown on the public page reviewed",
    note: "Licenses are used per scanned target and remain used for 30 days.",
  },
  {
    name: "CyCognito",
    href: "https://www.cycognito.com/",
    pricing: "No public price found",
    note: "The public product page describes external attack surface management; contact the vendor for a quote.",
  },
  {
    name: "Censys",
    href: "https://censys.com/resources/pricing/",
    pricing: "Credit packages start at $100",
    note: "Usage-based credits cover platform actions and datasets; not directly comparable to per-domain monitoring plans.",
  },
];

export default function HomePage() {
  const [status, setStatus] = useState<FormStatus>("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setStatus("submitting");
    setMessage("");

    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: data.get("email"),
          website: data.get("website"),
        }),
      });
      const result = (await response.json()) as { error?: string };
      if (!response.ok) throw new Error(result.error || "We couldn't submit your request. Please try again.");
      form.reset();
      setStatus("success");
      setMessage("You're on the list. We'll email you when early access is approved and when Orqelis is live.");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "We couldn't submit your request. Please try again.");
    }
  }

  return (
    <main className="page">
      <header className="header">
        <a className="brand" href="https://orqelis.com" aria-label="Orqelis">
          <span className="brand-mark">O</span>
          <span>ORQELIS</span>
        </a>
        <nav className="header-nav" aria-label="Main navigation">
          <a href="#features">V1 features</a>
          <a href="#comparison">Compare</a>
          <a href="#pricing">Pricing</a>
        </nav>
        <span className="header-note">EARLY ACCESS · V1 IN DEVELOPMENT</span>
      </header>

      <section className="hero" aria-labelledby="page-title">
        <div className="hero-copy">
          <p className="eyebrow">EXTERNAL SECURITY, MADE PRACTICAL</p>
          <h1 id="page-title">See what attackers see on your website.</h1>
          <p className="intro-copy">
            Orqelis maps your public web assets, checks them for real issues, and tells you what to fix first.
            It only scans domains you&apos;ve verified.
          </p>
          <a className="hero-link" href="#finding">See an example finding <span aria-hidden="true">↓</span></a>
        </div>

        <div className="form-card" id="early-access">
          <p className="eyebrow">ORQELIS EARLY ACCESS</p>
          <h2>Get early access</h2>
          <p className="form-copy">Join the list for an early-access update and launch announcement.</p>

          {status === "success" ? (
            <div className="success" role="status" aria-live="polite">
              <span className="success-icon" aria-hidden="true">✓</span>
              <p>{message}</p>
              <button
                className="text-button"
                type="button"
                onClick={() => {
                  setMessage("");
                  setStatus("idle");
                }}
              >
                Submit another email
              </button>
            </div>
          ) : (
            <form onSubmit={submit}>
              <label htmlFor="email">Work email</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                maxLength={254}
                placeholder="you@company.com"
                required
                disabled={status === "submitting"}
              />
              <div className="honeypot" aria-hidden="true">
                <label htmlFor="website">Leave this field blank</label>
                <input id="website" name="website" tabIndex={-1} autoComplete="off" />
              </div>
              <p className="consent">
                By joining, you agree to receive early-access and launch updates. See our{" "}
                <a href="/privacy">Privacy Policy</a>.
              </p>
              {message ? <p className="error" role="alert">{message}</p> : null}
              <button className="submit" type="submit" disabled={status === "submitting"}>
                {status === "submitting" ? "Joining..." : "Get early access"}
                <span aria-hidden="true">→</span>
              </button>
            </form>
          )}
          <p className="form-foot">NO SCANS · NO SPAM · JUST ACCESS UPDATES</p>
        </div>
      </section>

      <section className="audience section" aria-labelledby="audience-title">
        <p className="eyebrow">WHO IT&apos;S FOR</p>
        <h2 id="audience-title">Small SaaS teams and agencies without a security hire.</h2>
      </section>

      <section className="section sample-section" id="finding" aria-labelledby="finding-title">
        <div className="section-heading">
          <p className="eyebrow">A FINDING, NOT A WALL OF SCANNER OUTPUT</p>
          <h2 id="finding-title">Know what matters and what to do next.</h2>
        </div>
        <div className="sample-grid">
          <article className="finding-card">
            <div className="finding-topline">
              <span className="severity"><span aria-hidden="true">●</span> MEDIUM</span>
              <span className="finding-kind">HTTP SECURITY HEADER</span>
            </div>
            <h3>Missing HSTS header</h3>
            <p className="finding-host">app.example.com</p>
            <div className="finding-explanation">
              <h4>What&apos;s wrong</h4>
              <p>The site doesn&apos;t tell browsers to use HTTPS for future visits.</p>
              <h4>Why it matters</h4>
              <p>On an unsafe network, a visitor could be more vulnerable to a downgrade or interception attempt.</p>
              <h4>How to fix it</h4>
              <p>After confirming HTTPS works across the site and its subdomains, serve a Strict-Transport-Security header with an appropriate max-age.</p>
            </div>
            <p className="example-note">Illustrative example only. This is not a live scan result.</p>
          </article>
          <aside className="health-card" aria-label="Illustrative web health scores">
            <div className="health-heading">
              <div>
                <p className="eyebrow">WEB HEALTH</p>
                <h3>At a glance</h3>
              </div>
              <span className="health-score">76<span>/100</span></span>
            </div>
            {[
              { name: "TLS", score: 92, level: "good" },
              { name: "Headers", score: 68, level: "medium" },
              { name: "Exposure", score: 81, level: "good" },
              { name: "API", score: 63, level: "medium" },
            ].map((item) => (
              <div className="health-row" key={item.name}>
                <div className="health-label"><span>{item.name}</span><span>{item.score}</span></div>
                <div className="health-track"><span className={item.level} style={{ width: `${item.score}%` }} /></div>
              </div>
            ))}
            <p className="example-note">Illustrative scores, not real customer data.</p>
          </aside>
        </div>
      </section>

      <section className="section" id="features" aria-labelledby="features-title">
        <div className="section-heading">
          <p className="eyebrow">V1 · IN DEVELOPMENT</p>
          <h2 id="features-title">A focused first release.</h2>
          <p>These are the capabilities planned for V1. They are not available yet and may change before launch.</p>
        </div>
        <ul className="feature-list">
          {features.map((feature, index) => (
            <li key={feature}>
              <span className="feature-number">{String(index + 1).padStart(2, "0")}</span>
              <span>{feature}</span>
              <span className="feature-status">IN DEVELOPMENT</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="section reasons-section" aria-labelledby="reasons-title">
        <div className="section-heading">
          <p className="eyebrow">WHY TEAMS SWITCH</p>
          <h2 id="reasons-title">Security guidance that respects your time.</h2>
        </div>
        <div className="reason-grid">
          {[
            "Flat, predictable pricing with no surprise increases.",
            "Fewer false positives, with human-reviewed findings.",
            "Muted findings stay muted.",
            "Plain-English fixes, not raw scanner output.",
            "Fast, human support.",
          ].map((reason, index) => (
            <article className="reason-card" key={reason}>
              <span className="reason-index">0{index + 1}</span>
              <p>{reason}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section comparison-section" id="comparison" aria-labelledby="comparison-title">
        <div className="section-heading">
          <p className="eyebrow">PUBLIC PRICING SNAPSHOT</p>
          <h2 id="comparison-title">Different tools, different pricing models.</h2>
          <p>
            Orqelis is in development. This is a pricing-transparency snapshot, not a feature-for-feature
            verdict; the products cover different scopes and are not directly comparable.
          </p>
        </div>
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr><th scope="col">Product</th><th scope="col">Public price information</th><th scope="col">Pricing notes</th></tr>
            </thead>
            <tbody>
              {comparisons.map((item) => (
                <tr key={item.name}>
                  <th scope="row">
                    <a href={item.href} target={item.href.startsWith("http") ? "_blank" : undefined} rel="noreferrer">
                      {item.name}{item.href.startsWith("http") ? <span className="external-mark" aria-label=" (opens in a new tab)">↗</span> : null}
                    </a>
                  </th>
                  <td>{item.pricing}</td>
                  <td>{item.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="comparison-footnote">
          Competitor details are based on public information reviewed on October 25, 2026. Pricing and packaging
          can change; check each vendor&apos;s linked page for current terms.
        </p>
      </section>

      <section className="section pricing-section" id="pricing" aria-labelledby="pricing-title">
        <div className="section-heading">
          <p className="eyebrow">INDICATIVE PRICING · NOT LIVE</p>
          <h2 id="pricing-title">Straightforward plans for growing teams.</h2>
          <p>
            Proposed monthly prices for planning conversations. Orqelis has no live billing yet; final prices,
            plan limits, and terms may change before launch.
          </p>
        </div>
        <div className="pricing-grid">
          {plans.map((plan) => (
            <article className={`plan-card${plan.featured ? " plan-featured" : ""}`} key={plan.name}>
              {plan.featured ? <span className="plan-badge">FOR SMALL TEAMS</span> : null}
              <h3>{plan.name}</h3>
              <p className="plan-price">
                {plan.price}
                {plan.price.startsWith("$") ? <span> / month</span> : null}
              </p>
              <ul>
                <li>{plan.scans}</li>
                <li>{plan.assets}</li>
              </ul>
              <a className="plan-link" href="#early-access">Get early access <span aria-hidden="true">→</span></a>
            </article>
          ))}
        </div>
        <p className="pricing-footnote">Proposed limits shown for planning only. No payment is taken to join the waitlist.</p>
      </section>

      <section className="section roadmap-section" aria-labelledby="roadmap-title">
        <div className="section-heading">
          <p className="eyebrow">AFTER V1 · PLANNED</p>
          <h2 id="roadmap-title">A separate roadmap, not a launch promise.</h2>
        </div>
        <ul className="roadmap-list">
          {[
            "Nuclei checks",
            "Deeper API checks",
            "Staging environments",
            "Slack and Jira alerts",
            "Cloud checks",
            "Web application scanning",
            "A bounty hunter tier",
          ].map((item) => <li key={item}><span>{item}</span><span className="planned-tag">PLANNED</span></li>)}
        </ul>
      </section>

      <section className="section founder-section" aria-labelledby="founder-title">
        <p className="eyebrow">A NOTE FROM THE FOUNDER</p>
        <h2 id="founder-title">Security should be within reach of the people building the web.</h2>
        <p>
          I&apos;m building Orqelis because small teams face real risks on their public-facing websites, often
          without a security specialist to help. The goal is to make the important issues easier to see,
          understand, and fix.
        </p>
      </section>

      <section className="section trust-section" aria-labelledby="trust-title">
        <div>
          <p className="eyebrow">TRUST &amp; SAFETY</p>
          <h2 id="trust-title">Your scope. Your authorization.</h2>
          <p>
            Orqelis is in development. The scanner is being designed for read-only checks on domains you have
            verified control of; it will not make changes to scanned systems. No scan can start without domain
            verification.
          </p>
        </div>
        <div className="trust-links">
          <a href="/about-scanner">About our scanner <span aria-hidden="true">→</span></a>
          <a href="/privacy">Privacy Policy <span aria-hidden="true">→</span></a>
          <a href="mailto:support@waitlist.orqelis.dev">Contact Orqelis <span aria-hidden="true">→</span></a>
        </div>
      </section>

      <footer className="footer">
        <span>© {new Date().getFullYear()} Orqelis</span>
        <nav aria-label="Footer">
          <a href="/privacy">Privacy</a>
          <a href="/about-scanner">About our scanner</a>
          <a href="mailto:support@waitlist.orqelis.dev">Contact</a>
          <a href="mailto:support@waitlist.orqelis.dev">Waitlist email</a>
        </nav>
      </footer>
    </main>
  );
}
