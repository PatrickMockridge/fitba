import Link from "next/link";
import { CaseBenchmark } from "@/components/CaseBenchmark";
import { CaseClaimCard } from "@/components/CaseClaimCard";
import { CaseCoverage } from "@/components/CaseCoverage";
import { ContractPage } from "@/components/ContractPage";
import { getCase } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/claims/" },
  title: "Claims and evidence · fitba",
  description:
    "The published claims about Aberdeen's season, each with its evidence, status and the test that would change the view.",
};

export default function ClaimsPage() {
  const document = getCase();
  if (!document) {
    return (
      <ContractPage surface="claims" state="empty">
        <section className="page-head" data-contract="claims.hero">
          <p className="eyebrow">Claims and evidence</p>
          <h1>Claims and evidence</h1>
          <p className="lede">No claim document is published in this build.</p>
        </section>
      </ContractPage>
    );
  }
  return (
    <ContractPage surface="claims">
      <section className="page-head" data-contract="claims.hero">
        <p className="eyebrow">Claims and evidence</p>
        <h1>Claims and evidence</h1>
        <p className="lede">
          The published claims about the season, each with its count, status,
          evidence and the comparison that would change the view. This is an
          independent record, not a club briefing. The claims include the difficult
          numbers as well as the favourable ones.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/analysis/">
            Season overview
          </Link>
          <Link className="button button-ghost" href="/matchday/">
            Matchday
          </Link>
          <Link className="button button-ghost" href="/metrics/">
            Metrics and audit
          </Link>
        </div>
        <p className="fine-print">
          <span data-contract-indicator="confidence">
            Confidence is labelled per claim
          </span>{" "}
          · <span data-contract-indicator="unknown">Unknown stays unknown</span>
        </p>
      </section>

      <section className="section" data-contract="claims.register">
        {document.claims.map((claim) => (
          <CaseClaimCard claim={claim} key={claim.id} />
        ))}
      </section>

      <section className="section" data-contract="claims.benchmark">
        <CaseBenchmark benchmark={document.benchmark} />
      </section>

      <section className="section" data-contract="claims.coverage">
        <CaseCoverage coverage={document.coverage} />
      </section>

      <p className="fine-print">
        A claim can be supported, mixed, unsupported or not testable. Interpretation is
        labelled as interpretation; a correction changes a factual value against a public
        source and is recorded in <Link href="/corrections/">corrections</Link>.
      </p>
    </ContractPage>
  );
}
