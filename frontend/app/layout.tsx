import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Nav from "@/components/Nav";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "TurboRUL · Aircraft Engine Predictive Maintenance",
  description: "Machine-learning Remaining Useful Life estimation on NASA N-CMAPSS",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body className="bg-blueprint min-h-screen font-sans antialiased">
        <Nav />
        <main className="mx-auto max-w-7xl px-4 pb-24 pt-10">{children}</main>
        <footer className="border-t border-line py-6 text-center text-xs text-muted">
          NASA N-CMAPSS · Turbofan Engine Degradation Simulation-2 · Flask + Next.js
        </footer>
      </body>
    </html>
  );
}
