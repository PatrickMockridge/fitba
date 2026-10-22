import type { XgAggregate, XgDocument } from "@/lib/data";
import { formatDecimal, formatInterval, formatSigned } from "@/lib/format";

function scopeLabel(row: XgAggregate): string {
  if (row.scope === "last10") return "Last 10";
  if (row.scope === "era") return "Era";
  return row.season;
}

export function XgTable({ aggregates }: { aggregates: XgDocument["aggregates"] }) {
  return (
    <section className="card" data-contract="xg.aggregate">
      <div className="section-head">
        <div>
          <p className="eyebrow">fxG</p>
          <h2>Expected goals, with the model interval</h2>
        </div>
        <span className="badge badge-neutral">experimental</span>
      </div>
      <div className="table-wrap">
        <table className="league-table">
          <thead>
            <tr>
              <th>Scope</th>
              <th className="num">Matches</th>
              <th className="num">fxG</th>
              <th className="num">80% interval</th>
              <th className="num">Goals</th>
              <th className="num">Goals − fxG</th>
              <th className="num">80% interval</th>
            </tr>
          </thead>
          <tbody>
            {aggregates.map((row) => (
              <tr key={`${row.scope}-${row.season}`}>
                <td>{scopeLabel(row)}</td>
                <td className="num">{row.matches}</td>
                <td className="num">{row.fxg === null ? "—" : formatDecimal(row.fxg)}</td>
                <td className="num">{formatInterval(row.low, row.high)}</td>
                <td className="num">{row.goals}</td>
                <td className="num">
                  {row.goals_minus_fxg === null ? "—" : formatSigned(row.goals_minus_fxg)}
                </td>
                <td className="num">
                  {formatInterval(row.goals_minus_low, row.goals_minus_high)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        Totals over the scope; divide by matches for a per-match figure. The
        interval is the aggregate model interval. fxG is a shot-on-target
        conversion model: it carries conversion uncertainty and match-to-match
        overdispersion. Provider xG is shown separately on a fixture and is not
        blended into fxG.
      </p>
    </section>
  );
}
