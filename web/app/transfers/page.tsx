import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { TransferBoard } from "@/components/TransferBoard";
import { getTransferAudit, getTransfers } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/transfers/" }, title: "Transfers · fitba" };

export default function TransfersPage() {
  const data = getTransfers();
  const audit = getTransferAudit();
  if (!data) {
    return (
      <ContractPage surface="transfers" state="empty">
        <section className="empty-state" data-contract="transfers.empty">
          <h1>No transfer register published</h1>
          <p>
            Run <code>uv run fitba transfers</code> and then{" "}
            <code>uv run fitba publish</code>.
          </p>
        </section>
      </ContractPage>
    );
  }

  return (
    <ContractPage surface="transfers">
      <section className="page-head" data-contract="transfers.hero">
        <p className="eyebrow">Aberdeen · confirmed business</p>
        <h1>Transfers &amp; loans</h1>
        <p className="lede">
          The business that actually happened: permanent transfers, loans and
          free moves in and out of Pittodrie, from 2019-20 to the current
          window. No rumours, no &ldquo;in talks&rdquo; lane, and no invented
          fees.
        </p>
        <div className="hero-actions">
          <span className="badge badge-ok">
            {data.summary.confirmed} official-confirmed
          </span>
          <span className="badge badge-warn">
            {data.summary.curated} source-linked curated
          </span>
          <span className="badge badge-neutral">{data.summary.total} deals</span>
          {data.plausibility?.withheld ? (
            <span className="badge badge-warn">
              {data.plausibility.withheld} suspect row
              {data.plausibility.withheld === 1 ? "" : "s"} withheld
            </span>
          ) : null}
          <Link className="button button-ghost" href="/history/">
            The Cormack era
          </Link>
          <Link className="button button-ghost" href="/former-players/">
            Former players
          </Link>
        </div>
        <p className="fine-print">
          Audited from {data.coverage.audited_from ?? "2024-25"}; earlier windows
          are curated partial. Disclosed and reported fees are anchors; other
          permanent moves carry an inferred range. Undisclosed is never zero.
        </p>
      </section>

      <TransferBoard data={data} />

      {data.sell_on_clauses?.length ? (
        <section className="card" data-contract="transfers.sell-on">
          <div className="section-head">
            <div>
              <p className="eyebrow">Future income</p>
              <h2>Sell-on clauses</h2>
            </div>
            <span className="badge badge-neutral">
              {data.sell_on_summary.percentage_known} with a stated percentage
            </span>
          </div>
          <div className="table-wrap">
            <table className="league-table compact">
<caption className="fine-print">Confirmed transfers, loans and coverage.</caption>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Buyer</th>
                  <th>Sale</th>
                  <th>Clause</th>
                  <th>Confidence</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {data.sell_on_clauses.map((clause) => (
                  <tr key={clause.clause_id}>
                    <td className="strong">{clause.player_name}</td>
                    <td>{clause.buyer_club_name}</td>
                    <td>{formatDate(clause.sale_date)}</td>
                    <td>
                      {clause.sell_on_pct !== null
                        ? `${clause.sell_on_pct}%${
                            clause.basis === "profit"
                              ? " of profit"
                              : clause.basis === "gross_fee"
                                ? " of fee"
                                : ""
                          }`
                        : "Clause reported · % undisclosed"}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          clause.confidence === "confirmed" ? "badge-ok" : "badge-warn"
                        }`}
                        data-contract-indicator="confidence"
                      >
                        {clause.confidence}
                      </span>
                    </td>
                    <td className="fine-print">
                      {clause.source_urls.length ? (
                        clause.source_urls.map((url) => (
                          <a key={url} href={url} target="_blank" rel="noreferrer">
                            {url.includes("wikipedia.org") ? "Wikipedia" : "source"}
                          </a>
                        ))
                      ) : (
                        <span>reported; no allowed public URL</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="fine-print">{data.sell_on_summary.note}</p>
          <p className="fine-print">
            A reported clause is not a confirmed contract term. The register
            tracks it so future sale proceeds are not invisible; it does not
            assume the percentage or the basis.{" "}
            <Link href="/former-players/">Sell-on watch and former-player record →</Link>
          </p>
        </section>
      ) : null}

      <section className="card" data-contract="transfers.audit">
        <div className="card-head">
          <div>
            <p className="eyebrow">Completeness</p>
            <h2>Register completeness</h2>
          </div>
          <span className="badge badge-neutral">Report only</span>
        </div>
        {audit && audit.status === "ok" ? (
          <>
            <div className="stat-row four">
              <div className="stat-tile">
                <span className="stat-label">Established senior</span>
                <span className="stat-value">
                  {audit.summary.needs_review.established}
                </span>
                <span className="stat-note">needs review</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">Fringe senior</span>
                <span className="stat-value">{audit.summary.needs_review.fringe}</span>
                <span className="stat-note">needs review</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">Youth / development</span>
                <span className="stat-value">{audit.summary.needs_review.youth}</span>
                <span className="stat-note">tolerated gaps</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">Position coverage</span>
                <span className="stat-value">
                  {audit.summary.positions.specified}/
                  {audit.summary.positions.specified + audit.summary.positions.unknown}
                </span>
                <span className="stat-note">rows with a position</span>
              </div>
            </div>
            <p className="fine-print">
              Gaps: {audit.summary.gaps.open} open, {audit.summary.gaps.accepted}{" "}
              accepted, {audit.summary.gaps.resolved} resolved.
              {audit.summary.needs_review.unclassified
                ? ` ${audit.summary.needs_review.unclassified} unclassified row${
                    audit.summary.needs_review.unclassified === 1 ? "" : "s"
                  } still needs review.`
                : ""}{" "}
              Last audit {formatDate(audit.generated_at)}. Senior gaps are
              reported, not hidden; youth gaps are recorded and tolerated.
            </p>
          </>
        ) : (
          <p className="fine-print">
            <strong>Audit not run.</strong> Run{" "}
            <code>uv run fitba transfers --audit</code> after a window closes or
            at the start of a season.
          </p>
        )}
      </section>

      <section className="card" data-contract="transfers.coverage">
        <div className="card-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>How to read the register</h2>
          </div>
          <span className="badge badge-warn">Curated</span>
        </div>
        <p>{data.coverage.note}</p>
        <ul className="plain-list">
          <li>
            <strong>Confirmed:</strong> a licensed-feed record plus an official
            club announcement.
          </li>
          <li>
            <strong>Curated:</strong> a licensed-feed record cross-checked against
            the public season record; an official announcement link is shown where
            found.
          </li>
          <li data-contract-indicator="unknown">
            <strong>Undisclosed:</strong> a fee exists but is not public. It is
            never counted as zero; permanent moves get an inferred range, and
            loan fees are excluded from the net.
          </li>
          <li data-contract-indicator="unknown">
            <strong>Loan terms:</strong> end dates, recall and obligation clauses
            are unknown unless confirmed by an official source.
          </li>
        </ul>
        <p className="fine-print" data-contract-indicator="source">
          Sources: {data.sources.length} linked pages, including official AFC
          announcements and the Wikipedia season records. No raw feed rows are
          published.
        </p>
        <Link className="text-link" href="/sources/">
          Source and licence detail →
        </Link>
      </section>

      <p className="back-link">
        <Link href="/matchday/">← Matchday dashboard</Link>
      </p>
    </ContractPage>
  );
}
