import Link from "next/link";

export const metadata = {
  title: "Waitlist Privacy Policy | Orqelis",
  description: "How Orqelis collects and uses information submitted to its early-access waitlist.",
};

const sections = [
  {
    title: "1. Who is responsible",
    paragraphs: [
      "This notice applies to the Orqelis early-access waitlist at this website. The organization responsible for the waitlist is [LEGAL ENTITY NAME], at [POSTAL ADDRESS] (\"Orqelis,\" \"we,\" or \"us\"). For privacy questions or requests, contact [PRIVACY EMAIL]. These business contact details must be completed before publication.",
    ],
  },
  {
    title: "2. Information we collect",
    paragraphs: [
      "When you join the waitlist, we collect the email address you submit and the date and time the signup is recorded. We use an automated hidden form field to help detect spam; if that field is filled, the submission is discarded.",
      "Our hosting and infrastructure providers may process technical information needed to deliver and protect the site and API, such as IP address, request time, user-agent, and diagnostic or security logs. The waitlist does not ask for account credentials, security scan data, or sensitive personal information.",
    ],
  },
  {
    title: "3. How we use your information",
    paragraphs: [
      "We use your email address to record your interest in Orqelis, manage the early-access list, contact you about an early-access decision, and send a launch announcement. We do not use waitlist addresses for unrelated marketing. We may also use technical information to operate, secure, troubleshoot, and prevent abuse of the site and signup service.",
      "We process your signup information to take steps you request by joining the list and, where required, on the basis of your consent to receive these updates. You can withdraw that consent at any time by contacting [PRIVACY EMAIL].",
    ],
  },
  {
    title: "4. Where information is stored and shared",
    paragraphs: [
      "Waitlist records are stored in the Orqelis application database, hosted by the infrastructure provider configured for the API. The standalone waitlist website is hosted separately. These providers process information to host and operate the service on our behalf.",
      "If Resend is configured for the waitlist, we create a global Resend contact for the email address and may send an internal signup notification to the configured team inbox. Resend processes contact and email-delivery information under its own terms and privacy notice. Contact creation requires an API key with Contacts: Write permission; a segment or audience ID is not required.",
      "We do not sell waitlist personal information. We may disclose it where required by law, to protect the security and rights of people or the service, or in connection with a business reorganization subject to applicable safeguards.",
    ],
  },
  {
    title: "5. Retention",
    paragraphs: [
      "We keep waitlist information while it is useful for managing early access and launch communications, and for a reasonable period afterward to maintain suppression, security, and compliance records. We periodically review stored entries and remove or anonymize information that is no longer needed, unless law requires longer retention.",
      "If a contact has also been created in Resend, removing the application database entry does not automatically remove the separate Resend contact. Contact us to request removal from both systems. The precise retention schedule should be confirmed before this notice is treated as a contractual guarantee.",
    ],
  },
  {
    title: "6. Your choices and privacy rights",
    paragraphs: [
      "You can unsubscribe from waitlist communications or ask us to access, correct, delete, restrict, or otherwise handle your personal information by emailing [PRIVACY EMAIL]. Depending on where you live, you may have additional rights under applicable privacy law, including the right to complain to a data-protection authority. We may need to verify your request before acting on it.",
      "If you withdraw permission to receive updates, we will stop sending waitlist communications. This does not affect processing that took place before withdrawal or records we must retain for legitimate legal or security reasons.",
    ],
  },
  {
    title: "7. International processing and security",
    paragraphs: [
      "Our service providers may process information in countries other than the country where you live. Where applicable law requires it, appropriate safeguards will be used for international transfers.",
      "We use reasonable administrative, technical, and organizational measures intended to protect waitlist information. No internet transmission or storage method can be guaranteed completely secure.",
    ],
  },
  {
    title: "8. Children",
    paragraphs: [
      "The waitlist is intended for people interested in an organizational security product and is not directed to children. Do not submit a child's personal information. If you believe a child has submitted information, contact [PRIVACY EMAIL] so we can review it.",
    ],
  },
  {
    title: "9. Changes and contact",
    paragraphs: [
      "We may update this notice when our practices or legal requirements change. We will publish the revised notice here and update its effective date. For questions or privacy requests, contact [PRIVACY EMAIL].",
    ],
  },
];

export default function WaitlistPrivacyPage() {
  return (
    <main className="policy-page">
      <header className="policy-header">
        <Link href="/" className="policy-brand">ORQELIS · EARLY ACCESS</Link>
        <Link href="/" className="policy-back">Back to waitlist</Link>
      </header>
      <article className="policy-content">
        <p className="eyebrow">PRIVACY · WAITLIST</p>
        <h1>Waitlist Privacy Policy</h1>
        <p className="policy-date">Effective date: 19 October 2026 · Last updated: 19 October 2026</p>
        <p className="policy-notice">
          Publication draft: complete the bracketed business and privacy contact details and have this notice
          reviewed against actual hosting, provider, and legal requirements before launch.
        </p>
        <p className="policy-intro">
          This notice explains how Orqelis handles information when you join the separate Orqelis early-access
          waitlist. It applies to this waitlist website and its signup service, not to customer accounts or use of
          the Orqelis security platform, which are covered by separate notices.
        </p>
        {sections.map((section) => (
          <section className="policy-section" key={section.title}>
            <h2>{section.title}</h2>
            {section.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </section>
        ))}
      </article>
      <footer className="policy-footer">
        <span>© {new Date().getFullYear()} Orqelis</span>
        <Link href="/">Return to the waitlist</Link>
      </footer>
    </main>
  );
}
