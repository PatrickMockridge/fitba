import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { getManifest } from "@/lib/data";

export const metadata: Metadata = {
  title: "fitba — Scottish football, Aberdeen-first",
  description:
    "League tables, Aberdeen analysis and player scouting across the Scottish football pyramid.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const manifest = getManifest();
  return (
    <html lang="en-GB">
      <body>
        <header className="site-header">
          <div className="wrap header-inner">
            <Link href="/" className="brand">
              <span className="brand-mark">f</span>
              <span>
                <strong>fitba</strong>
                <small>Scottish football, Aberdeen-first</small>
              </span>
            </Link>
            <nav className="nav" aria-label="Main">
              <Link href="/scotland/">Pyramid</Link>
              <Link href="/clubs/aberdeen/">Aberdeen</Link>
              <Link href="/scouting/">Scouting</Link>
              <Link href="/loans/">Loans</Link>
              <Link href="/methodology/">Method</Link>
            </nav>
          </div>
        </header>

        <main className="wrap">{children}</main>

        <footer className="site-footer">
          <div className="wrap footer-inner">
            <div>
              <strong>fitba</strong> · a non-commercial Scottish football research project.
              Not affiliated with Aberdeen FC, the SPFL or any data provider.
            </div>
            <div className="footer-meta">
              <FreshnessBadge manifest={manifest} />
              <Link href="/status/">Data status</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
