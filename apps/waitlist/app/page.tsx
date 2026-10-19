"use client";

import { FormEvent, useState } from "react";

type FormStatus = "idle" | "submitting" | "success" | "error";

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
        <span className="header-note">EARLY ACCESS · V1 IN DEVELOPMENT</span>
      </header>

      <section className="content" aria-labelledby="page-title">
        <div className="intro">
          <p className="eyebrow">SECURITY FOR THE INTELLIGENT WORLD</p>
          <h1 id="page-title">
            Your attack surface.
            <br />
            <span>In the clear.</span>
          </h1>
          <p className="intro-copy">
            A clearer way for security teams to understand web exposure. Get early access to Orqelis.
          </p>
          <ul className="benefits">
            <li>Verified web assets</li>
            <li>Human-reviewed findings</li>
            <li>Rules-led detection</li>
          </ul>
        </div>

        <div className="form-card">
          <p className="eyebrow">ORQELIS EARLY ACCESS</p>
          <h2>Join the waitlist</h2>
          <p className="form-copy">Be first to hear when early access is ready.</p>

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
              <label htmlFor="email">Email address</label>
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
                {status === "submitting" ? "Joining..." : "Join the waitlist"}
                <span aria-hidden="true">→</span>
              </button>
            </form>
          )}
          <p className="form-foot">ACCESS UPDATE · LAUNCH UPDATE</p>
        </div>
      </section>

      <section className="features" aria-labelledby="features-title">
        <div className="features-heading">
          <p className="eyebrow">BUILT FOR EXTERNAL WEB EXPOSURE</p>
          <h2 id="features-title">See the features taking shape</h2>
          <p>
            Orqelis V1 is focused on authorized web-asset security. These are the core capabilities being
            developed for early access.
          </p>
        </div>
        <div className="feature-grid">
          <article className="feature-card">
            <span className="feature-number">01 / SCOPE</span>
            <h3>Verify the assets you own</h3>
            <p>
              Register domains for assessment and verify control with a DNS record before a scan can start.
              Scans stay within the authorized, verified scope.
            </p>
            <span className="feature-tag">DNS verification</span>
          </article>
          <article className="feature-card">
            <span className="feature-number">02 / DISCOVER</span>
            <h3>Map external exposure</h3>
            <p>
              Build a clearer picture of discovered subdomains, reachable web services, and the public
              technologies they reveal.
            </p>
            <span className="feature-tag">Asset discovery</span>
          </article>
          <article className="feature-card">
            <span className="feature-number">03 / DETECT</span>
            <h3>Review concrete security checks</h3>
            <p>
              Inspect TLS configuration and HTTP security headers, with deterministic findings that give
              teams observable issues to investigate.
            </p>
            <span className="feature-tag">TLS · HTTP · Rules</span>
          </article>
          <article className="feature-card">
            <span className="feature-number">04 / UNDERSTAND</span>
            <h3>Turn findings into next steps</h3>
            <p>
              Review findings and incident context in one dashboard, with AI-assisted explanations,
              remediation suggestions, and reports for people to evaluate.
            </p>
            <span className="feature-tag">Human-led review</span>
          </article>
        </div>
        <p className="features-note">
          Orqelis is in early development. Capabilities may change before early access; scans require
          authorization and do not make changes to target systems.
        </p>
      </section>

      <footer className="footer">
        <span>© {new Date().getFullYear()} Orqelis</span>
        <span><a href="/privacy">Privacy Policy</a> · Built for security-minded teams</span>
      </footer>
    </main>
  );
}
