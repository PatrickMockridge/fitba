import Link from "next/link";
import type { ScoutingLeader } from "@/lib/data";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : formatPercentValue(value, 1);
}

export function ScoutingTeamLens({
  label,
  definition,
  threshold,
  leaders,
  coverage,
  scenario = false,
}: {
  label: string;
  definition: string;
  threshold: number | null;
  leaders: ScoutingLeader[];
  coverage: Record<string, number>;
  scenario?: boolean;
}) {
  const ranked = leaders;
  return (
    <section className="card" data-contract="scouting.team-lens">
      <div className="card-head">
        <div>
          <p className="eyebrow">Team context</p>
          <h2>{label}</h2>
        </div>
        <span className={`badge ${scenario ? "badge-warn" : "badge-neutral"}`}>
          {scenario ? "Reader scenario" : "Published defaults"} · league PPG ≤{" "}
          {threshold === null ? "—" : formatInteger(threshold)}
        </span>
      </div>
      <p>
        {scenario
          ? "Reader scenario: the active lenses select these players; they are not the published default leaders. "
          : ""}
        {definition} The lift is a contrast between the player&apos;s role-adjusted percentile
        and the team&apos;s points-per-game percentile; it is not a valuation, forecast or
        recommendation.
      </p>
      <p className="fine-print">
        {formatInteger(coverage.with_standings ?? 0)}/{formatInteger(coverage.leagues ?? 0)}{" "}
        leagues with a current table, {formatInteger(coverage.teams ?? 0)} teams. A league
        without a table is unknown, not zero-strength.
      </p>
      {ranked.length ? (
        <div className="table-wrap">
          <table className="league-table compact">
            <caption className="fine-print">
              Players with a positive team lift at teams in the bottom of their league by
              points per game. Club is the current club; League is where the statistics were
              produced.
            </caption>
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col">Club</th>
                <th scope="col">League</th>
                <th scope="col">Team</th>
                <th className="num" scope="col">Team PPG %</th>
                <th className="num" scope="col">Adj %</th>
                <th className="num" scope="col">Lift</th>
                <th className="num" scope="col">Priority</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((leader) => (
                <tr key={`${leader.player_id}-${leader.league_slug}`}>
                  <td>
                    <Link href={`/scouting/player/${leader.player_id}/`}>{leader.name}</Link>
                  </td>
                  <td>
                    {leader.club}
                    {leader.stats_club && leader.stats_club !== leader.club ? (
                      <span className="muted"> · stats at {leader.stats_club}</span>
                    ) : null}
                  </td>
                  <td>{leader.league_name}</td>
                  <td>
                    {leader.team_rank === null || leader.team_count === null
                      ? "—"
                      : `${leader.team_rank}/${leader.team_count}`}
                    {leader.team_points !== null ? (
                      <span className="muted"> · {leader.team_points} pts</span>
                    ) : null}
                  </td>
                  <td className="num">{pct(leader.team_points_percentile)}</td>
                  <td className="num">{pct(leader.adjusted_percentile)}</td>
                  <td className="num">{formatDecimal(leader.team_lift ?? 0, 1)}</td>
                  <td className="num">
                    {leader.scouting_priority === null ||
                    leader.scouting_priority === undefined
                      ? "—"
                      : formatDecimal(leader.scouting_priority, 1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">
          {scenario
            ? "No player meets these lenses."
            : "No player meets the team-context lens at the current coverage."}
        </p>
      )}
    </section>
  );
}
