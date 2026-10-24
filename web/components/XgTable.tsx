import type { XgAggregate, XgDocument } from "@/lib/data";
import { formatDecimal, formatInteger, formatInterval, formatSigned } from "@/lib/format";

function scopeLabel(row: XgAggregate): string {
  if (row.scope === "last10") return "Last 10";
  if (row.scope === "era") return "Era";
  return row.season;
}

function goalInterval(low: number | null, high: number | null): string {
  if (low === null || high === null) return "—";
  return `${formatInteger(low)}–${formatInteger(high)}`;
}

export function XgTable({ aggregates }: { aggregates: XgDocument["aggregates"] }) {
  return (
    <section className="card" data-contract="xg.aggregate">
      <div className="section-head">
        <div>
          <p className="eyebrow">fxG</p>
          <h2>Expected goals, with a model range and a goals range</h2>
        </div>
        <span className="badge badge-neutral">experimental</span>
      </div>
      <div className="table-wrap">
        <table className="league-table">
<caption className="fine-print">
              fxG aggregates with an 80% model range, an 80% goals range and goals.
            </caption>
          <thead>
            <tr>
              <th>Scope</th>
              <th className="num">Matches</th>
              <th className="num">fxG</th>
              <th className="num">80% model range</th>
              <th className="num">xG per shot</th>
              <th className="num">Goals</th>
              <th className="num">80% goals range</th>
              <th className="num">Goals − fxG</th>
            </tr>
          </thead>
          <tbody>
            {aggregates.map((row) => (
              <tr key={`${row.scope}-${row.season}`}>
                <td>{scopeLabel(row)}</td>
                <td className="num">{row.matches}</td>
                <td className="num">{row.fxg === null ? "—" : formatDecimal(row.fxg)}</td>
                <td className="num">{formatInterval(row.low, row.high)}</td>
                <td className="num">
                  {row.xg_per_shot === null ? "—" : formatDecimal(row.xg_per_shot, 3)}
                </td>
                <td className="num">{row.goals}</td>
                <td className="num">{goalInterval(row.goals_low, row.goals_high)}</td>
                <td className="num">
                  {row.goals_minus_fxg === null ? "—" : formatSigned(row.goals_minus_fxg)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        Scottish Premiership only. Cup and European fxG is published on each
        match page and is not added to these league aggregates. Totals over the
        scope; divide by matches for a per-match figure. The 80% model range is
        the uncertainty in the fxG estimate. The 80% goals range is the spread
        of goals the same chances would produce; it is not a confidence interval
        for team quality and it is not a result prediction. Per-match intervals
        are never added together. fxG is a team-match estimate from shots, shot
        zones and penalties; it is not provider xG, and provider xG is never
        blended into it. Current-season shot counts use API-Football;
        historical league shots use football-data. Goals − fxG uses the final
        score, including own goals; own goals are not part of the shot model.
      </p>
    </section>
  );
}
