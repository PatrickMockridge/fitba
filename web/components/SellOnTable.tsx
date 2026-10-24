import type { FormerSellOnClause } from "@/lib/data";
import { formatDate, formatGbp, formatInteger } from "@/lib/format";

function receiptLabel(clause: FormerSellOnClause): string {
  const receipt = clause.receipt;
  if (receipt.status === "computed" && receipt.receipt_gbp !== null) {
    return formatGbp(receipt.receipt_gbp);
  }
  if (receipt.missing_inputs.length) {
    return `Not computable · ${receipt.missing_inputs.join(", ")}`;
  }
  if (receipt.status === "not_triggered") return "No trigger";
  if (receipt.status === "no_sale") return "No sale";
  return receipt.status;
}

export function SellOnTable({
  clauses,
  summary,
}: {
  clauses: FormerSellOnClause[];
  summary: Record<string, number | string | null>;
}) {
  return (
    <section className="card" data-contract="former.sell-on">
      <div className="section-head">
        <div>
          <p className="eyebrow">Future income</p>
          <h2>Sell-on watch</h2>
        </div>
        <span className="badge badge-neutral">
          {formatInteger(Number(summary.computed ?? 0))} of{" "}
          {formatInteger(Number(summary.total ?? 0))} computable
        </span>
      </div>
      <div className="table-wrap">
        <table className="league-table compact">
          <caption className="fine-print">
            A receipt is shown only where the clause percentage, basis and subsequent fee are all publicly evidenced. No receipt computed is not zero future income.
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Sale</th>
              <th scope="col">Buyer</th>
              <th scope="col">Clause</th>
              <th scope="col">Confidence</th>
              <th scope="col">Subsequent move</th>
              <th scope="col">Trigger</th>
              <th className="num" scope="col">Implied share</th>
              <th scope="col">Source</th>
            </tr>
          </thead>
          <tbody>
            {clauses.map((clause) => (
              <tr key={clause.clause_id}>
                <td className="strong">{clause.player_name}</td>
                <td>{formatDate(clause.sale_date)}</td>
                <td>{clause.buyer_club_name}</td>
                <td>
                  {clause.sell_on_pct === null
                    ? "Percentage undisclosed"
                    : `${clause.sell_on_pct}% ${clause.basis === "profit" ? "of profit" : clause.basis === "gross_fee" ? "of fee" : ""}`}
                </td>
                <td>
                  <span className={`badge ${clause.confidence === "confirmed" ? "badge-ok" : "badge-warn"}`}>
                    {clause.confidence}
                  </span>
                </td>
                <td>
                  {clause.event
                    ? `${clause.event.date} · ${clause.event.from_club_name ?? "—"} to ${clause.event.to_club_name ?? "—"}`
                    : "—"}
                </td>
                <td>{clause.event_status.replace("_", " ")}</td>
                <td className="num">{receiptLabel(clause)}</td>
                <td className="fine-print">
                  {clause.source_urls.length ? (
                    clause.source_urls.map((url) => (
                      <a key={url} href={url} target="_blank" rel="noreferrer">
                        source
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
      <p className="fine-print">
        {String(summary.note ?? "")} The implied share is a gross amount before instalments, add-ons, agent and solidarity deductions, all of which are unknown.
      </p>
    </section>
  );
}
