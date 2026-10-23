import type { ScoutingLayerZero } from "@/lib/data";
import { formatDate, formatDecimal, formatInteger } from "@/lib/format";

const STATUS_LABEL: Record<string, string> = {
  out: "Out",
  doubtful: "Doubtful",
  suspended: "Suspended",
  returned: "Returned",
  available: "Available",
  unknown: "Unknown",
};

function statusBadge(status: string) {
  const modifier =
    status === "out" || status === "suspended"
      ? "badge-warn"
      : status === "available" || status === "returned"
        ? "badge-ok"
        : "badge-neutral";
  return <span className={`badge ${modifier}`}>{STATUS_LABEL[status] ?? status}</span>;
}

function sourceLabel(url: string | null): string {
  if (!url) return "No public source";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "Source";
  }
}

export function ScoutingLayerZeroTable({ items }: { items: ScoutingLayerZero[] }) {
  if (!items.length) {
    return (
      <div className="empty-state" data-contract-indicator="unknown">
        <p>
          No verified official AFC team-news entry is published for this build. Availability
          is unknown, not fit. A source is added only when the official club page names the
          player and the entry can be dated.
        </p>
      </div>
    );
  }
  return (
    <div className="table-wrap">
      <table className="league-table compact">
        <caption className="fine-print">
          Verified availability entries from official AFC team news. Unknown players are not
          listed; minutes are not used as proof of fitness.
        </caption>
        <thead>
          <tr>
            <th scope="col">Player</th>
            <th scope="col">Role</th>
            <th scope="col">Status</th>
            <th className="num" scope="col">Current mins</th>
            <th className="num" scope="col">Prior rating</th>
            <th className="num" scope="col">Prior mins</th>
            <th scope="col">Source</th>
            <th scope="col">Verified</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.player_id}>
              <td className="strong">{item.name}</td>
              <td>{item.role_label ?? item.family_label}</td>
              <td>
                {statusBadge(item.status)}
                {item.first_choice ? (
                  <span className="badge badge-neutral"> first-choice evidence</span>
                ) : null}
              </td>
              <td className="num">{formatInteger(item.minutes)}</td>
              <td className="num">
                {item.prior?.rating === null || item.prior?.rating === undefined
                  ? "—"
                  : formatDecimal(item.prior.rating)}
                {item.prior ? <span className="muted"> · {item.prior.season}</span> : null}
              </td>
              <td className="num">
                {item.prior ? formatInteger(item.prior.minutes) : "—"}
              </td>
              <td data-contract-indicator="source">
                {item.source_url ? (
                  <a className="text-link" href={item.source_url} rel="noreferrer">
                    {sourceLabel(item.source_url)}
                  </a>
                ) : (
                  "—"
                )}
              </td>
              <td>{item.verified_at ? formatDate(item.verified_at) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
