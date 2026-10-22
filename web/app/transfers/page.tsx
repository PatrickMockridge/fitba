import Link from "next/link";
import { EmptyState } from "@/components/EmptyState";
import { LegendDisclosure } from "@/components/LegendDisclosure";
import { MetricStrip } from "@/components/MetricStrip";
import { PageHeader } from "@/components/PageHeader";
import { TableFrame, Th } from "@/components/TableFrame";
import { TransferBoard } from "@/components/TransferBoard";
import { formatDate } from "@/lib/format";
import { getTransferAudit, getTransfers } from "@/lib/data";

export const metadata = { title: "Transfers · fitba" };

function money(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  const sign = value < 0 ? "−" : "+";
  return `${sign}£${(Math.abs(value) / 1_000_000).toFixed(1)}m`;
}

export default function TransfersPage() {
  const data = getTransfers();
  const audit = getTransferAudit();
  if (!data) {
    return (
      <EmptyState
        title="No transfer register published"
        body="The confirmed transfer register will appear after the next publish."
        action={
          <Link className="button button-ghost" href="/status/">
            Data status
          </Link>
        }
      />
    );
  }

  const currentKey = data.window_groups?.recent?.[0];
  const currentWindow = data.windows.find((window) => window.key === currentKey);
  const netLow = currentWindow?.inferred_net_low_gbp;
  const netHigh = currentWindow?.inferred_net_high_gbp;
  const windowLabel = currentWindow?.label ?? "Current window";

  return (
    <>
      <PageHeader
        eyebrow="Aberdeen · transfer register"
        title="Who arrived and who left?"
        summary={`${data.summary.total} moves · ${data.summary.period ?? "2019/20"}. ${windowLabel}: ${currentWindow?.arrivals ?? 0} in, ${currentWindow?.departures ?? 0} out.`}
      />

      <MetricStrip
        columns={5}
        items={[
          {
            label: "Moves",
            value: data.summary.total,
            note: `${data.summary.players} players`,
          },
          { label: "In", value: currentWindow?.arrivals ?? "—", note: windowLabel },
          { label: "Out", value: currentWindow?.departures ?? "—", note: windowLabel },
          {
            label: "Net",
            value:
              netLow === null || netLow === undefined || netHigh === null || netHigh === undefined
                ? "—"
                : `${money(netLow)} to ${money(netHigh)}`,
            note: "inferred",
          },
          {
            label: "Confirmed",
            value: data.summary.confirmed,
            note: "official announcement",
          },
        ]}
      />

      <TransferBoard data={data} />

      {data.sell_on_clauses?.length ? (
        <section className="section">
          <div className="section-head">
            <div>
              <h2>Sell-on clauses</h2>
            </div>
            <span className="muted">
              {data.sell_on_summary.percentage_known} with a stated percentage
            </span>
          </div>
          <TableFrame
            label="Sell-on clauses"
            caption="Aberdeen sell-on clauses on former players"
          >
            <thead>
              <tr>
                <Th>Player</Th>
                <Th>Buyer</Th>
                <Th>Sale</Th>
                <Th>Clause</Th>
                <Th>Confidence</Th>
                <Th>Source</Th>
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
                      : "Percentage undisclosed"}
                  </td>
                  <td>{clause.confidence}</td>
                  <td>
                    {clause.source_urls.length ? (
                      clause.source_urls.map((url) => (
                        <a key={url} href={url} target="_blank" rel="noreferrer">
                          {url.includes("wikipedia.org") ? "Wikipedia" : "Source"}
                        </a>
                      ))
                    ) : (
                      <span>Reported</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableFrame>
        </section>
      ) : null}

      <LegendDisclosure title="How the register is built">
        <p>
          Fees are disclosed, reported or estimated. Undisclosed is never zero;
          permanent moves without a public fee carry an inferred range, and loan
          fees are excluded from net spend. A negative net means income exceeds
          spend.
        </p>
        <p>
          {data.summary.confirmed} moves carry an official announcement; the rest
          are curated from the provider feed and Wikipedia season records.
        </p>
        {audit && audit.status === "ok" ? (
          <p>
            Completeness: {audit.summary.needs_review.established} established and{" "}
            {audit.summary.needs_review.fringe} fringe senior moves need review;{" "}
            {audit.summary.gaps.accepted} gaps accepted;{" "}
            {audit.summary.positions.specified}/
            {audit.summary.positions.specified + audit.summary.positions.unknown} rows
            have a position.
          </p>
        ) : null}
        <p>
          <Link href="/methodology/">Method</Link> ·{" "}
          <Link href="/sources/">Sources</Link> · <Link href="/status/">Data status</Link>
        </p>
      </LegendDisclosure>
    </>
  );
}
