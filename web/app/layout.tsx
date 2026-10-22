import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { GullMark } from "@/components/GullMark";
import { getManifest } from "@/lib/data";

export const metadata: Metadata = {
  title: "fitba — Aberdeen FC, without the noise.",
  description:
    "An independent, data-driven record of Aberdeen FC: matchday, squad, recruitment and the Cormack era, with sources and uncertainty.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const manifest = getManifest();
  return (
    <html lang="en-GB">
      <body>
        <header className="site-header" data-contract="site.header">
          <div className="wrap header-inner">
            <Link href="/" className="brand">
              <span className="brand-mark">f</span>
              <span>
                <strong>fitba</strong>
                <small>Aberdeen FC, without the noise.</small>
              </span>
            </Link>
            <nav className="nav" aria-label="Main">
              <Link href="/matchday/">Matchday</Link>
              <Link href="/themes/">Themes</Link>
              <Link href="/squad/">Squad</Link>
              <Link href="/recruitment/">Off the pitch</Link>
              <Link href="/history/">The Cormack era</Link>
              <Link href="/news/">News &amp; rumours</Link>
            </nav>
          </div>
        </header>

        <main className="wrap">{children}</main>

        <footer className="site-footer" data-contract="site.footer">
          <div className="wrap footer-inner">
            <div>
              <strong>fitba</strong> · Aberdeen FC, without the noise. An independent,
              non-commercial research project. Not affiliated with Aberdeen FC, the
              SPFL, the SFA or any data provider.
              <div className="footer-place">
                <GullMark />
                <span>Aberdeen · North Sea · 1903</span>
              </div>
            </div>
            <div className="footer-meta">
              <FreshnessBadge manifest={manifest} />
              <Link href="/methodology/">Method</Link>
              <Link href="/about/">About</Link>
              <Link href="/sources/">Sources</Link>
              <Link href="/status/">Data status</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
