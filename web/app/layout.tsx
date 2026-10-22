import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import "./system.css";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { ScrollToTop } from "@/components/ScrollToTop";
import { SiteNav } from "@/components/SiteNav";
import { ThemeSwitcher } from "@/components/ThemeSwitcher";
import { getManifest } from "@/lib/data";

const SITE_URL = "https://patrickmockridge.github.io/fitba/";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "fitba — Aberdeen FC, without the noise.",
  description:
    "An independent, data-driven record of Aberdeen FC: matchday, squad, recruitment and the Cormack era, with sources and uncertainty.",
  openGraph: {
    type: "website",
    siteName: "fitba",
    title: "fitba — Aberdeen FC, without the noise.",
    description:
      "An independent, data-driven record of Aberdeen FC, with sources and uncertainty.",
    url: SITE_URL,
  },
  twitter: {
    card: "summary",
    title: "fitba — Aberdeen FC, without the noise.",
    description:
      "An independent, data-driven record of Aberdeen FC, with sources and uncertainty.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const manifest = getManifest();
  return (
    <html lang="en-GB" suppressHydrationWarning>
      <body>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <ScrollToTop />
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var t=window.localStorage.getItem('fitba-theme');if(t&&['merkland','red-matchday','aurora','floodlight'].indexOf(t)>-1){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();",
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              name: "fitba",
              url: SITE_URL,
              description:
                "An independent, data-driven record of Aberdeen FC, with sources and uncertainty.",
            }),
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
            <SiteNav />
          </div>
        </header>

        <main className="wrap" id="main-content">
          {children}
        </main>

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
              <Link href="/corrections/">Corrections</Link>
              <Link href="/status/">Data status</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
