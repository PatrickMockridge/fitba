import Link from "next/link";
import type { ScoutingLeagueSummary } from "@/lib/data";
import { formatInteger, formatPercentValue } from "@/lib/format";

const STATUS_LABEL: Record<string, string> = {
  ok: "Searchable",
  partial: "Partial",
  no_player_stats: "No player stats",
  error: "Provider error",
  stale: "Stale",
  unknown: "Unknown",
};

function statusBadge(league: ScoutingLeagueSummary) {
  if (league.status === "no_player_stats") {
    return (
      <span className="badge badge-neutral" data-contract-indicator="unknown">
        No player stats
      </span>
    );
  }
  if (league.status === "error") {
    return <span className="badge badge-warn">Provider error</span>;
  }
  if (league.searchable) {
    return <span className="badge badge-ok">Searchable</span>;
  }
  return <span className="badge badge-neutral">{STATUS_LABEL[league.status] ?? league.status}</span>;
}

export function ScoutingLeagueIndex({ leagues }: { leagues: ScoutingLeagueSummary[] }) {
  return (
    <>
      <div className="table-wrap">
        <table className="league-table compact">
          <caption className="fine-print">
            The configured scouting universe. Each page searches one league; percentiles are
            within that league and role family, never across leagues.
          </caption>
          <thead>
            <tr>
              <th scope="col">League</th>
              <th scope="col">Country</th>
              <th className="num" scope="col">Players</th>
              <th className="num" scope="col">Rated</th>
              <th className="num" scope="col">450+</th>
              <th className="num" scope="col">Role coverage</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {leagues.map((league) => (
              <tr key={league.id}>
                <td>
                  <Link className="text-link" href={league.href}>
                    {league.name}
                  </Link>
                </td>
                <td>{league.country || "—"}</td>
                <td className="num">{formatInteger(league.players)}</td>
                <td className="num">{formatInteger(league.rated)}</td>
                <td className="num">{formatInteger(league.with_minutes_450)}</td>
                <td className="num">
                  {league.players
                    ? formatPercentValue(league.role_coverage * 100, 1)
                    : "—"}
                </td>
                <td>{statusBadge(league)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        Scottish Championship, League One and League Two have starting-XI lineups but no
        current-season player statistics in the provider feed. Their pages say so and do not
        zero-fill. The same applies to any other league shown as “No player stats”.
      </p>
    </>
  );
}
