"use client";

import Link from "next/link";
import { useEffect } from "react";
import { ContractPage } from "@/components/ContractPage";

export default function ThemesRedirectPage() {
  useEffect(() => {
    document.title = "Data analysis · fitba";
    const target = new URL("../analysis/", window.location.href);
    if (window.location.hash) target.hash = window.location.hash;
    window.location.replace(target.toString());
  }, []);

  return (
    <ContractPage surface="themes" state="redirect">
      <section className="page-head" data-contract="themes.redirect">
        <p className="eyebrow">Moved</p>
        <h1>Data analysis</h1>
        <p className="lede">
          This page has moved to <strong>Data analysis</strong>. If the redirect
          does not start, use the link below.
        </p>
        <p>
          <Link className="button" href="/analysis/">
            Open Data analysis
          </Link>
        </p>
      </section>
    </ContractPage>
  );
}
