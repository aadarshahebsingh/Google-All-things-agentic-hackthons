import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FounderShortcut — Your AI co-founder",
  description: "Validates, researches, and executes startup ideas autonomously.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
