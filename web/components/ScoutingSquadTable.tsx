import type { ScoutingSquadRow } from "@/lib/data";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";

function num(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : formatDecimal(value, 2);
}

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : formatPercentValue(value, 1);
}

export function ScoutingSquadTable({ rows }: { rows: ScoutingSquadRow[] }) {
  if (!rows.length) {
    return (
      <p className="empty-state" data-contract-indicator="unknown">
        No Aberdeen player has enough competitive minutes for the position profile in this
        build.
      </p>
    );
  }
  return (
    <>
      <div className="table-wrap">
        <table className="league-table compact">
          <caption className="fine-print">
            Aberdeen&apos;s registered squad by role family, competitive matches only. Rates
            are per 90 minutes; pass completion and duel wins are provider percentages. A dash
            means the value is unavailable, not zero.
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Role</th>
              <th className="num" scope="col">Mins</th>
              <th className="num" scope="col">Rating</th>
              <th className="num" scope="col">Pct</th>
              <th className="num" scope="col">G+A/90</th>
              <th className="num" scope="col">Shots/90</th>
              <th className="num" scope="col">Dribbles/90</th>
              <th className="num" scope="col">Passes/90</th>
              <th className="num" scope="col">Pass %</th>
              <th className="num" scope="col">Key passes/90</th>
              <th className="num" scope="col">Tackles/90</th>
              <th className="num" scope="col">Interceptions/90</th>
              <th className="num" scope="col">Duels won %</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.player_id}>
                <td className="strong">{row.name}</td>
                <td>{row.role_label}</td>
                <td className="num">{formatInteger(row.minutes)}</td>
                <td className="num">{num(row.rating)}</td>
                <td className="num">
                  {row.rating_percentile === null
                    ? "—"
                    : formatPercentValue(row.rating_percentile, 1)}
                </td>
                <td className="num">{num(row.goals_assists_p90)}</td>
                <td className="num">{num(row.shots_p90)}</td>
                <td className="num">{num(row.dribbles_success_p90)}</td>
                <td className="num">{num(row.passes_completed_p90)}</td>
                <td className="num">{pct(row.pass_completion_pct)}</td>
                <td className="num">{num(row.key_passes_p90)}</td>
                <td className="num">{num(row.tackles_p90)}</td>
                <td className="num">{num(row.interceptions_p90)}</td>
                <td className="num">{pct(row.duel_win_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        Successful passes are the provider&apos;s pass total multiplied by its accuracy.
        Forward and progressive passes, carries, pressures and aerial wins are not in the
        licensed feed; they are shown as unavailable, not inferred.
      </p>
    </>
  );
}
