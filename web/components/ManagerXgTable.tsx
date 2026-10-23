import type { XgManagerSplit } from "@/lib/data";
import { formatDecimal, formatSigned } from "@/lib/format";

function dec(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : formatDecimal(value);
}

function signed(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : formatSigned(value);
}

function stint(row: XgManagerSplit) {
  if (row.scope === "season_context") return "Season total";
  if (!row.stint_start) return "—";
  return `${row.stint_start.slice(0, 10)} – ${
    row.stint_end ? row.stint_end.slice(0, 10) : "present"
  }`;
}

function providerBasis(row: XgManagerSplit) {
  if (row.provider_basis === "actual_partial") {
    return `actual (${row.provider_actual_matches}/${row.matches})`;
  }
  return row.provider_basis;
}

function providerFor(row: XgManagerSplit) {
  if (row.provider_basis === "actual" || row.provider_basis === "actual_partial") {
    return dec(row.provider_actual_for);
  }
  if (row.provider_basis === "estimate") return dec(row.provider_estimate_for);
  return "—";
}

function providerAgainst(row: XgManagerSplit) {
  if (row.provider_basis === "actual" || row.provider_basis === "actual_partial") {
    return dec(row.provider_actual_against);
  }
  if (row.provider_basis === "estimate") return dec(row.provider_estimate_against);
  return "—";
}

export function ManagerXgTable({ rows }: { rows: XgManagerSplit[] }) {
  if (!rows.length) return null;
  return (
    <section className="card" data-contract="xg.managers">
      <div className="section-head">
        <div>
          <p className="eyebrow">Manager comparison</p>
          <h2>Robinson&apos;s league spells compared</h2>
        </div>
        <span className="badge badge-neutral">League only</span>
      </div>
      <div className="table-wrap">
        <table className="league-table compact">
          <caption className="fine-print">
            League only. Managers are attributed by match date. Provider xG is
            actual where supplied and a calibrated estimate otherwise; the two are
            never summed.
          </caption>
          <thead>
            <tr>
              <th scope="col">Manager</th>
              <th scope="col">Stint</th>
              <th scope="col">Season</th>
              <th scope="col" className="num">
                Matches
              </th>
              <th scope="col" className="num">
                fxG for
              </th>
              <th scope="col" className="num">
                fxG against
              </th>
              <th scope="col" className="num">
                Goals for
              </th>
              <th scope="col" className="num">
                Goals against
              </th>
              <th scope="col" className="num">
                Goals − fxG for
              </th>
              <th scope="col" className="num">
                Goals − fxG against
              </th>
              <th scope="col" className="num">
                Provider xG for
              </th>
              <th scope="col" className="num">
                Provider xG against
              </th>
              <th scope="col">Provider basis</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`${row.season}-${row.stint_id ?? "context"}`}
                className={
                  row.comparison_role === "current"
                    ? "is-highlight"
                    : row.scope === "season_context"
                      ? "muted"
                      : undefined
                }
              >
                <td className="strong">{row.manager}</td>
                <td>{stint(row)}</td>
                <td>{row.season}</td>
                <td className="num">{row.matches}</td>
                <td className="num">{dec(row.fxg_for)}</td>
                <td className="num">{dec(row.fxg_against)}</td>
                <td className="num">{row.goals_for}</td>
                <td className="num">{row.goals_against}</td>
                <td className="num">{signed(row.goals_minus_fxg_for)}</td>
                <td className="num">{signed(row.goals_minus_fxg_against)}</td>
                <td className="num">{providerFor(row)}</td>
                <td className="num">{providerAgainst(row)}</td>
                <td>{providerBasis(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        Nine matches per Robinson league spell; the comparison is descriptive, not
        a causal verdict. The full 2025-26 row is context, not a fourth spell.
      </p>
    </section>
  );
}
