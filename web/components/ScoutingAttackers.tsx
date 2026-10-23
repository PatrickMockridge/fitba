import Link from "next/link";
import type {
  ScoutingAttackers,
  ScoutingPriorityConfig,
} from "@/lib/data";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";
import { leaderList } from "@/components/ScoutingArchetypes";

function value(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? "—" : formatDecimal(value, digits);
}

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : formatPercentValue(value, 1);
}

export function ScoutingAttackers({
  attackers,
  priority,
  scenario = false,
}: {
  attackers: ScoutingAttackers;
  priority: ScoutingPriorityConfig;
  scenario?: boolean;
}) {
  return (
    <>
      <section className="card" data-contract="scouting.attackers">
        <div className="card-head">
          <div>
            <p className="eyebrow">Attackers</p>
            <h2>Assist bias and goal bias</h2>
          </div>
          <span className={`badge ${scenario ? "badge-warn" : "badge-neutral"}`}>
            {scenario ? "Reader scenario" : "Separate profiles"}
          </span>
        </div>
        <p>
          {scenario
            ? "Reader scenario: the active lenses select these players; they are not the published default leaders. "
            : ""}
          The attack is split into two explainable lenses rather than one combined
          “goal contributor” score. The assist-biased profile weights completed passes, key
          passes, pass completion, assists and successful dribbles; the goal-biased profile
          weights goals, shot volume, conversion and total goal contribution, and deliberately
          excludes pass and dribble volume. Each list is ordered by its own profile score with
          the U23 and European multipliers applied, not by the value-index priority: ranking
          both by priority produced the same order. The feed carries no crosses, so key passes
          are the closest available creation signal.
        </p>
        <div className="grid two-col">
          <section className="mini-block">
            <p className="eyebrow">Assist-biased contributor</p>
            <h3>{attackers.assist_bias.label}</h3>
            {leaderList(
              attackers.assist_bias.leaders,
              priority,
              scenario ? "No player meets these lenses." : undefined,
            )}
            <Link className="text-link" href="/scouting/search/#assist_creator">
              Filter by this profile →
            </Link>
          </section>
          <section className="mini-block">
            <p className="eyebrow">Goal-scoring contributor</p>
            <h3>{attackers.goal_bias.label}</h3>
            {leaderList(
              attackers.goal_bias.leaders,
              priority,
              scenario ? "No player meets these lenses." : undefined,
            )}
            <Link className="text-link" href="/scouting/search/#goal_scorer">
              Filter by this profile →
            </Link>
          </section>
        </div>
      </section>

      <section className="card" data-contract="scouting.goal-scoring">
        <div className="card-head">
          <div>
            <p className="eyebrow">Goal scoring</p>
            <h2>Goal-scoring leaders</h2>
          </div>
          <span className="badge badge-neutral">Ordered by goals /90</span>
        </div>
        <p>
          {scenario
            ? "Reader scenario: the active lenses select these players; the order remains goals per 90. "
            : ""}
          A dedicated scoring lens for forwards and attacking midfielders at the pool minutes
          threshold. The order is goals per 90, then goal contribution and minutes; it is not
          the composite profile and not a recommendation.
        </p>
        <div className="table-wrap">
          <table className="league-table compact">
            <caption className="fine-print">
              Goals per 90 at 450+ minutes. Club is the current club; League is where the
              2026-27 statistics were produced. A dash means the feed does not supply the value.
            </caption>
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col">Club</th>
                <th scope="col">League</th>
                <th className="num" scope="col">Age</th>
                <th className="num" scope="col">Mins</th>
                <th className="num" scope="col">Goals</th>
                <th className="num" scope="col">Assists</th>
                <th className="num" scope="col">Goals/90</th>
                <th className="num" scope="col">G+A/90</th>
                <th className="num" scope="col">Shots/90</th>
                <th className="num" scope="col">Conversion</th>
                <th className="num" scope="col">Priority</th>
              </tr>
            </thead>
            <tbody>
              {attackers.goal_scoring.map((player) => (
                <tr key={`${player.player_id}-${player.league_slug}`}>
                  <td>
                    <Link href={`/scouting/player/${player.player_id}/`}>
                      {player.name}
                    </Link>
                  </td>
                  <td>
                    {player.club}
                    {player.stats_club && player.stats_club !== player.club ? (
                      <span className="muted"> · stats at {player.stats_club}</span>
                    ) : null}
                  </td>
                  <td>{player.league_name}</td>
                  <td className="num">
                    {value(player.age, 0)}
                    {player.age !== null && player.age <= priority.u23_max_age ? (
                      <span className="badge badge-neutral"> U23</span>
                    ) : null}
                  </td>
                  <td className="num">{formatInteger(player.minutes)}</td>
                  <td className="num">{value(player.goals, 0)}</td>
                  <td className="num">{value(player.assists, 0)}</td>
                  <td className="num">{value(player.goals_p90)}</td>
                  <td className="num">{value(player.goals_assists_p90)}</td>
                  <td className="num">{value(player.shots_p90)}</td>
                  <td className="num">{pct(player.conversion_pct)}</td>
                  <td className="num">{value(player.scouting_priority, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print">{attackers.note}</p>
      </section>
    </>
  );
}
