import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Orqelis | Website security for small teams",
  description: "Join the Orqelis waitlist for practical, verified-domain web security checks.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
