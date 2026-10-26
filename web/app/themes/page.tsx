"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function ThemesRedirectPage() {
  useEffect(() => {
    document.title = "Season overview · fitba";
    const target = new URL("../analysis/", window.location.href);
    if (window.location.hash) target.hash = window.location.hash;
    window.location.replace(target.toString());
  }, []);

  return (
    <div className="contract-page" data-contract-page="themes" data-contract-state="redirect">
      <section className="page-head" data-contract="themes.redirect">
        <p className="eyebrow">Moved</p>
        <h1>Season overview</h1>
        <p className="lede">
          This page has moved to <strong>Season overview</strong>. If the redirect
          does not start, use the link below.
        </p>
        <p>
          <Link className="button" href="/analysis/">
            Open Season overview
          </Link>
        </p>
      </section>
    </div>
  );
}
