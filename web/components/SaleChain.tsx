import Link from "next/link";
import type {
  FormerAberdeenProfile,
  FormerPlayerSeasons,
  FormerSellOnClause,
} from "@/lib/data";
import { formatDate, formatGbp } from "@/lib/format";

function feeText(clause: FormerSellOnClause): string {
  if (clause.sell_on_pct !== null) return `${clause.sell_on_pct}%`;
  return "percentage undisclosed";
}

function receiptText(clause: FormerSellOnClause): string {
  const receipt = clause.receipt;
  const status = receipt.status.replaceAll("_", " ");
  const missing = receipt.missing_inputs.length
    ? ` (missing: ${receipt.missing_inputs.join(", ")})`
    : "";
  return `receipt ${status}${missing}`;
}

export function SaleChain({
  player,
  seasons,
}: {
  player: FormerAberdeenProfile;
  seasons: FormerPlayerSeasons | null;
}) {
  const departure = player.departure;
  const clause = player.sell_on;
  const postSeasons = seasons?.post_seasons ?? [];
  const moves = seasons?.transfer_chain ?? [];
  const coverage = seasons?.coverage ?? null;

  return (
    <section className="sale-chain" data-contract="former.sale-chain">
      <div className="section-head">
        <div>
          <p className="eyebrow">Departure, after and sell-on</p>
          <h3>Sale chain</h3>
        </div>
        <span className="badge badge-neutral">Published link by link</span>
      </div>
      <p className="fine-print">
        Each step is a published fact. A missing fee, clause input or receipt
        stays unknown; the chain does not infer money or call a sale good or bad.
      </p>
      <ol className="sale-chain-list">
        <li>
          <strong>Departure</strong> · {departure.date ? formatDate(departure.date) : "date unknown"} ·{" "}
          {departure.to_club_name ?? "club unknown"} · {departure.kind ?? "move"} ·{" "}
          {departure.fee_display ?? "fee unknown"}
          {departure.is_rival ? ` · rival: ${departure.rival_name ?? "yes"}` : ""}
        </li>
        <li>
          <strong>After Aberdeen</strong> ·{" "}
          {postSeasons.length
            ? `${postSeasons.length} covered league season${postSeasons.length === 1 ? "" : "s"}`
            : "no covered post-Aberdeen league season"}
          {coverage ? (
            <>
              {" "}
              · {coverage.present_seasons.length} of{" "}
              {coverage.expected_seasons.length} expected seasons present
              {coverage.missing_seasons.length
                ? ` (missing: ${coverage.missing_seasons.join(", ")})`
                : ""}
            </>
          ) : null}
          {moves.length ? (
            <ul className="plain-list chain-moves">
              {moves.map((move) => (
                <li key={`${move.date}-${move.to_club_name}-${move.kind}`}>
                  {formatDate(move.date)} · {move.from_club_name ?? "—"} →{" "}
                  {move.to_club_name ?? "—"} · {move.kind}
                </li>
              ))}
            </ul>
          ) : null}
        </li>
        <li>
          <strong>Sell-on clause</strong> ·{" "}
          {clause
            ? `${feeText(clause)} · basis ${clause.basis} · confidence ${clause.confidence}`
            : "no clause recorded"}
          {clause?.event ? (
            <>
              {" "}
              · trigger: {clause.event.date ? formatDate(clause.event.date) : "date unknown"}{" "}
              · {clause.event.from_club_name ?? "—"} →{" "}
              {clause.event.to_club_name ?? "—"} ·{" "}
              {clause.event.fee_display ?? "fee unknown"}
            </>
          ) : clause ? (
            " · no subsequent permanent transfer in the covered record"
          ) : null}
        </li>
        <li>
          <strong>Receipt</strong> ·{" "}
          {clause
            ? `${receiptText(clause)}${
                clause.receipt.receipt_gbp !== null
                  ? ` · ${formatGbp(clause.receipt.receipt_gbp)}`
                  : ""
              }`
            : "not applicable"}
        </li>
        <li>
          <strong>Now</strong> ·{" "}
          {player.post_career.current.club_name ?? "current or last-known club unknown"}
          {" · "}
          {player.post_career.current.coverage === "current"
            ? "current-season provider row"
            : "last known"}
        </li>
      </ol>
      {clause ? (
        <p className="fine-print">
          Clause sources:{" "}
          {clause.source_urls.length
            ? clause.source_urls.map((url, index) => (
                <span key={url}>
                  {index ? " · " : null}
                  <Link className="text-link" href={url}>
                    source {index + 1}
                  </Link>
                </span>
              ))
            : "none published"}
          . A receipt is computed only from an evidenced percentage, an allowed
          basis, a public subsequent fee and, for a profit basis, the original fee.
        </p>
      ) : null}
    </section>
  );
}
