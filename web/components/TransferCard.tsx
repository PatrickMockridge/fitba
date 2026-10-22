import { PlayerLink } from "@/components/PlayerLink";
import type { TransferRecord } from "@/lib/data";
import { formatDate } from "@/lib/format";

const KIND_LABEL: Record<string, string> = {
  permanent: "Permanent",
  loan: "Loan",
  free: "Free",
  loan_return: "Loan return",
};

const KIND_CLASS: Record<string, string> = {
  permanent: "badge-ok",
  loan: "badge-warn",
  free: "badge-neutral",
  loan_return: "badge-neutral",
};

function sourceLabel(url: string): string {
  if (url.includes("afc.co.uk")) return "AFC announcement";
  if (url.includes("wikipedia.org")) return "Wikipedia";
  return "Source";
}

function gbp(value: number) {
  return `£${value.toLocaleString("en-GB")}`;
}

function estimateRange(low: number | null | undefined, high: number | null | undefined) {
  if (low === null || low === undefined || high === null || high === undefined) {
    return null;
  }
  return `${gbp(low)}–${gbp(high)}`;
}

export function TransferCard({
  transfer,
  contract,
}: {
  transfer: TransferRecord;
  contract?: string;
}) {
  const inbound = transfer.direction === "in";
  const estimate = transfer.fee_estimate;
  const range = estimateRange(estimate?.fee_low_gbp, estimate?.fee_high_gbp);
  const valueRange = estimateRange(
    estimate?.market_value_low_gbp,
    estimate?.market_value_high_gbp,
  );
  const feeLabel =
    estimate?.basis === "reported" && estimate.fee_low_gbp !== null
      ? `Reported ${gbp(estimate.fee_low_gbp)}`
      : transfer.fee_display;
  const estimateNote =
    estimate?.basis === "modelled" && range
      ? `Inferred ${range}`
      : estimate?.basis === "loan" && valueRange
        ? `Loan fee unknown · value ${valueRange}`
        : null;
  return (
    <article
      className={`transfer-card ${inbound ? "is-in" : "is-out"}`}
      id={`transfer-${transfer.transfer_id}`}
      data-contract={contract}
    >
      <div className="transfer-card-head">
        <span className={`badge ${KIND_CLASS[transfer.transfer_kind] ?? "badge-neutral"}`}>
          {inbound ? "IN" : "OUT"} · {KIND_LABEL[transfer.transfer_kind] ?? transfer.transfer_kind}
        </span>
        <span
          className={
            transfer.verification_status === "confirmed"
              ? "badge badge-ok"
              : "badge badge-warn"
          }
          data-contract="transfers.card.verification"
        >
          {transfer.verification_status}
        </span>
      </div>

      <h3>
        <PlayerLink name={transfer.player_name} href={transfer.player_href} />
      </h3>
      <p className="transfer-meta" data-contract="transfers.card.identity">
        {transfer.position ?? "Position unknown"} ·{" "}
        {transfer.nationality ?? "Nationality unknown"} · {transfer.season}{" "}
        {transfer.window === "other" ? "out of window" : transfer.window}
      </p>

      <div className="transfer-clubs">
        <span>{transfer.from_club_name}</span>
        <span className="transfer-arrow">→</span>
        <span>{transfer.to_club_name}</span>
      </div>

      <div className="transfer-foot" data-contract="transfers.card.fee">
        <span className="transfer-fee">{feeLabel}</span>
        <span className="muted">{formatDate(transfer.date_effective)}</span>
      </div>
      {estimateNote ? (
        <p
          className="fine-print"
          title={`Confidence: ${estimate?.confidence ?? "unknown"}`}
          data-contract-indicator="confidence"
        >
          {estimateNote}
        </p>
      ) : null}

      {transfer.transfer_kind === "loan" ||
      transfer.loan_end_date ||
      transfer.recall_clause ||
      transfer.obligation_to_buy ? (
        <p className="fine-print" data-contract="transfers.card.loan-terms">
          Loan terms:{" "}
          {[
            transfer.loan_end_date ? `until ${formatDate(transfer.loan_end_date)}` : null,
            transfer.recall_clause ? "recall clause" : null,
            transfer.obligation_to_buy ? "obligation to buy" : null,
          ]
            .filter(Boolean)
            .join(" · ") || "not confirmed by a public source"}
        </p>
      ) : null}

      {transfer.source_urls.length ? (
        <div
          className="transfer-sources"
          data-contract="transfers.card.sources"
          data-contract-indicator="source"
        >
          {transfer.source_urls.map((url) => (
            <a key={url} href={url} target="_blank" rel="noreferrer">
              {sourceLabel(url)}
            </a>
          ))}
        </div>
      ) : null}
    </article>
  );
}
