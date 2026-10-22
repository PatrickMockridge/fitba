import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { getFixtureIndex } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const metadata = {
  title: "Match record · fitba",
  description:
    "Every played Aberdeen fixture in the Cormack era, with the depth the record supports.",
};

export default function MatchesPage() {
  const index = getFixtureIndex();
  if (!index || !index.fixtures.length) {
    return (
      <ContractPage surface="matches" state="empty">
        <section className="page-head" data-contract="matches.hero">
          <p className="eyebrow">Matches</p>
          <h1>Match record</h1>
          <p className="lede">
            No played fixtures are published in this build. Run{" "}
            <code>uv run fitba publish</code> to generate the record.
          </p>
        </section>
      </ContractPage>
    );
  }
  const seasons = Array.from(new Set(index.fixtures.map((row) => row.season))).sort();
  return (
    <ContractPage surface="matches">
      <section className="page-head" data-contract="matches.hero">
        <p className="eyebrow">Cormack era</p>
        <h1>Match record</h1>
        <p className="lede">
          Every played Aberdeen fixture, with the score, the events, the lineups
          and the measured stats. The depth label says what the feed can show;
          it is not a claim that the rest does not exist.
        </p>
        <p className="fine-print">
          {index.count} played fixtures.{" "}
          <Link className="text-link" href="/analysis/xg/">
            fxG model and aggregates →
          </Link>{" "}
          <Link className="text-link" href="/analysis/">
            Data analysis →
          </Link>{" "}
          <Link className="text-link" href="/matchday/">
            Matchday →
          </Link>{" "}
          <Link className="text-link" href="/history/">
            The Cormack era →
          </Link>
        </p>
      </section>

      {seasons.map((season) => {
        const rows = index.fixtures.filter((row) => row.season === season);
        return (
          <section className="card" key={season} data-contract="matches.season">
            <div className="section-head">
              <div>
                <p className="eyebrow">{season}</p>
                <h2>{rows.length} played fixtures</h2>
              </div>
            </div>
            <div className="table-wrap">
              <table className="league-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Competition</th>
                    <th>Home</th>
                    <th className="num">Score</th>
                    <th>Away</th>
                    <th>Result</th>
                    <th>Depth</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.fixture_id}>
                      <td>{formatDate(row.date)}</td>
                      <td>{row.competition_name}</td>
                      <td>{row.home_team_name}</td>
                      <td className="num">
                        <Link className="text-link" href={row.href}>
                          {row.home_goals ?? "—"}–{row.away_goals ?? "—"}
                        </Link>
                      </td>
                      <td>{row.away_team_name}</td>
                      <td>{row.aberdeen_result}</td>
                      <td>{row.depth}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </ContractPage>
  );
}
