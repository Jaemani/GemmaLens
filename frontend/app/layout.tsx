import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaperLens",
  description: "Academic document language learning harness"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
