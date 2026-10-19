import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Orqelis Early Access",
  description: "Join the Orqelis early access waitlist.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
