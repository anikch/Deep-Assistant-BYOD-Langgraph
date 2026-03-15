import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Assistant PoC - Deep Research Agent",
  description: "Multi-user session-isolated research assistant with agentic capabilities",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
