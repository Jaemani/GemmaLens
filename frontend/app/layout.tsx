import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GemmaLens",
  description: "GemmaLens: Multimodal Language Learning from Any Content"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
