import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { MatchArchiveSearch } from "@/components/MatchArchiveSearch";
import { getFixtureIndex, getSearchIndex } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/matches/" },
  title: "Match record · fitba",
  description:
    "Every played Aberdeen fixture in the Cormack era, with the depth the record supports.",
};

function resultLabel(row: {
  home_penalties?: number | null;
  away_penalties?: number | null;
  aberdeen_is_home?: boolean;
  aberdeen_result: string;
}) {
  if (row.home_penalties == null || row.away_penalties == null) {
    return row.aberdeen_result;
  }
  const aberdeenHome = row.aberdeen_is_home ?? true;
  const aberdeenPens = aberdeenHome ? row.home_penalties : row.away_penalties;
  const opponentPens = aberdeenHome ? row.away_penalties : row.home_penalties;
  const won = aberdeenPens > opponentPens;
  return won
    ? `Won ${aberdeenPens}–${opponentPens} pens`
    : `Lost ${opponentPens}–${aberdeenPens} pens`;
}

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
  const publishedHrefs = new Set(index.fixtures.map((row) => row.href));
  const searchEntries = getSearchIndex().filter(
    (entry) => entry.type === "match" && entry.href && publishedHrefs.has(entry.href),
  );
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
        <nav className="badge-row" aria-label="Match seasons">
          {seasons.map((season) => (
            <a className="badge badge-neutral" key={season} href={`#season-${season}`}>
              {season}
            </a>
          ))}
        </nav>
        <MatchArchiveSearch entries={searchEntries} />
      </section>

      {seasons.map((season) => {
        const rows = index.fixtures.filter((row) => row.season === season);
        return (
          <section
            className="card"
            key={season}
            id={`season-${season}`}
            data-contract="matches.season"
          >
            <div className="section-head">
              <div>
                <p className="eyebrow">{season}</p>
                <h2>{rows.length} played fixtures</h2>
              </div>
            </div>
            <div className="table-wrap">
              <table className="league-table">
                <caption className="fine-print">
                  {season}: {rows.length} played fixtures. Depth is the highest
                  record class available; the match page lists every class.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Competition</th>
                    <th scope="col">Home</th>
                    <th scope="col" className="num">
                      Score
                    </th>
                    <th scope="col">Away</th>
                    <th scope="col">Result</th>
                    <th scope="col">Depth</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.fixture_id}>
                      <td>{formatDate(row.date)}</td>
                      <td>{row.competition_name}</td>
                      <td>{row.home_team_name}</td>
                      <td className="num">
                        <Link
                          className="text-link"
                          href={row.href}
                          prefetch={false}
                          aria-label={`${row.home_team_name} ${row.home_goals ?? "—"}–${row.away_goals ?? "—"} ${row.away_team_name}, ${formatDate(row.date)}`}
                        >
                          {row.home_goals ?? "—"}–{row.away_goals ?? "—"}
                        </Link>
                      </td>
                      <td>{row.away_team_name}</td>
                      <td>{resultLabel(row)}</td>
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
