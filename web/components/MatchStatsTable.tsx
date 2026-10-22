import type { FixtureDocument } from "@/lib/data";

function value(input: number | string | null): string {
  if (input === null || input === undefined) return "—";
  return String(input);
}

export function MatchStatsTable({
  stats,
  home,
  away,
  aberdeenIsHome,
}: {
  stats: FixtureDocument["stats"];
  home: string;
  away: string;
  aberdeenIsHome: boolean;
}) {
  const homeTeam = aberdeenIsHome ? "aberdeen" : "opponent";
  const awayTeam = aberdeenIsHome ? "opponent" : "aberdeen";
  return (
    <section
      className="card match-stats-table"
      data-contract="match.stats"
      data-team-split="aberdeen-opponent"
    >
      <div className="section-head">
        <div>
          <p className="eyebrow">Match stats</p>
          <h2>What the feed measured</h2>
        </div>
      </div>
      <div className="table-wrap">
        <table className="league-table">
          <caption className="fine-print">
            {home} and {away}, with Aberdeen highlighted in red.
          </caption>
          <thead>
            <tr>
              <th scope="col">Stat</th>
              <th scope="col" className="num" data-team={homeTeam}>
                {home}
              </th>
              <th scope="col" className="num" data-team={awayTeam}>
                {away}
              </th>
              <th scope="col">Source</th>
              <th scope="col">Basis</th>
            </tr>
          </thead>
          <tbody>
            {stats.rows.map((row) => (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td className="num" data-team={homeTeam}>
                  {value(row.home)}
                </td>
                <td className="num" data-team={awayTeam}>
                  {value(row.away)}
                </td>
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
