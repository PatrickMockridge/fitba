import Link from "next/link";
import { CaseBenchmark } from "@/components/CaseBenchmark";
import { CaseClaimCard } from "@/components/CaseClaimCard";
import { CaseCoverage } from "@/components/CaseCoverage";
import { ContractPage } from "@/components/ContractPage";
import { XgTable } from "@/components/XgTable";
import { getCase, getXg } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/analysis/" },
  title: "Data analysis · fitba",
  description:
    "Aberdeen's team, squad and chairman's record, with the evidence, the counts and what would change the view.",
};

export default function DataAnalysisPage() {
  const data = getCase();
  if (!data) {
    return (
      <ContractPage surface="analysis" state="empty">
        <section className="page-head" data-contract="case.hero">
          <p className="eyebrow">Data analysis</p>
          <h1>Data analysis</h1>
          <p className="lede">
            No data analysis document is published in this build. Run{" "}
            <code>uv run fitba publish</code> to generate it.
          </p>
        </section>
      </ContractPage>
    );
  }

  const xg = getXg();

  return (
    <ContractPage surface="analysis">
      <section className="page-head" data-contract="case.hero">
        <p className="eyebrow">Team · Squad · Chairman's record</p>
        <h1>Data analysis</h1>
        <p className="lede">{data.thesis}</p>
        <p className="fine-print">
          Generated {formatDate(String(data.generated_at).slice(0, 10))}.
        </p>
      </section>

      <section className="card case-frame" data-contract="case.frame">
        <div className="section-head">
          <div>
            <p className="eyebrow">{data.chairman_frame.label}</p>
            <h2>What the club set out to do</h2>
          </div>
        </div>
        <p>{data.chairman_frame.text}</p>
        <p className="fine-print">
          Source: {data.chairman_frame.source}. {data.chairman_frame.note}
        </p>
      </section>

      <section className="card case-opinion" data-contract="case.opinion">
        <div className="section-head">
          <div>
            <p className="eyebrow">{data.owner_view.label}</p>
            <h2>The argument to test</h2>
          </div>
          <span className="badge badge-neutral">{data.owner_view.attribution}</span>
        </div>
        <p>{data.owner_view.text}</p>
      </section>

      <p className="fine-print case-howto">
        Each claim below gives the count, the status, the evidence, what better
        data would settle and what would change the view. Method and definitions
        are linked, not repeated before the argument.
      </p>

      <div className="case-stack">
        {data.claims.map((claim) => (
          <CaseClaimCard key={claim.id} claim={claim} />
        ))}
      </div>

      {xg?.matches?.length ? (
        <>
          <XgTable aggregates={xg.aggregates} />
          <p className="fine-print" data-contract="analysis.xg-link">
            fxG is descriptive while the provider-xG gate fails. It is not a
            performance verdict.{" "}
            <Link className="text-link" href="/analysis/xg/">
              fxG model, evaluation and coverage →
            </Link>{" "}
            <Link className="text-link" href="/matches/">
              Match record →
            </Link>
          </p>
        </>
      ) : null}

      <CaseBenchmark benchmark={data.benchmark} />
      <CaseCoverage coverage={data.coverage} />

      <section className="card" data-contract="case.links">
        <div className="section-head">
          <div>
            <p className="eyebrow">Go deeper</p>
            <h2>Where the evidence comes from</h2>
          </div>
        </div>
        <ul className="link-list">
          <li>
            <Link href="/matchday/">Matchday</Link>
          </li>
          <li>
            <Link href="/squad/">Squad</Link>
          </li>
          <li>
            <Link href="/recruitment/">Recruitment</Link>
          </li>
          <li>
            <Link href="/transfers/">Transfers</Link>
          </li>
          <li>
            <Link href="/history/">The Cormack era</Link>
          </li>
          <li>
            <Link href="/methodology/">Methodology</Link>
          </li>
          <li>
            <Link href="/metrics/">Metrics and audit</Link>
          </li>
          <li>
            <Link href="/sources/">Sources</Link>
          </li>
        </ul>
      </section>
    </ContractPage>
  );
}
