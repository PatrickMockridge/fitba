import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import "./system.css";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { ThemeSwitcher } from "@/components/ThemeSwitcher";
import { getManifest } from "@/lib/data";

export const metadata: Metadata = {
  title: "fitba — Aberdeen FC, without the noise.",
  description:
    "An independent, data-driven record of Aberdeen FC: matchday, squad, recruitment and the Cormack era, with sources and uncertainty.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const manifest = getManifest();
  return (
    <html lang="en-GB" suppressHydrationWarning>
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var t=window.localStorage.getItem('fitba-theme');if(t&&['merkland','red-matchday','aurora','floodlight'].indexOf(t)>-1){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();",
          }}
        />
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
              <Link href="/analysis/">Data analysis</Link>
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
            </div>
            <div className="footer-meta">
              <ThemeSwitcher />
              <FreshnessBadge manifest={manifest} />
              <Link href="/analysis/">Data analysis</Link>
              <Link href="/methodology/">Method</Link>
              <Link href="/about/">About</Link>
              <Link href="/sources/">Sources</Link>
              <Link href="/metrics/">Metrics</Link>
              <Link href="/status/">Data status</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
