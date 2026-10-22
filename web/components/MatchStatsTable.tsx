import type { FixtureDocument } from "@/lib/data";

function value(input: number | string | null): string {
  if (input === null || input === undefined) return "—";
  return String(input);
}

export function MatchStatsTable({
  stats,
  home,
  away,
}: {
  stats: FixtureDocument["stats"];
  home: string;
  away: string;
}) {
  return (
    <section className="card" data-contract="match.stats">
      <div className="section-head">
        <div>
          <p className="eyebrow">Match stats</p>
          <h2>What the feed measured</h2>
        </div>
      </div>
      <div className="table-wrap">
        <table className="league-table">
          <thead>
            <tr>
              <th>Stat</th>
              <th className="num">{home}</th>
              <th className="num">{away}</th>
              <th>Source</th>
              <th>Basis</th>
            </tr>
          </thead>
          <tbody>
            {stats.rows.map((row) => (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td className="num">{value(row.home)}</td>
                <td className="num">{value(row.away)}</td>
                <td>{row.source}</td>
                <td>{row.basis}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {stats.rows.length === 0 ? (
        <p className="fine-print">
          Team statistics are unavailable for this fixture. The score, timeline
          and lineups remain on the page.
        </p>
      ) : null}
    </section>
  );
}
