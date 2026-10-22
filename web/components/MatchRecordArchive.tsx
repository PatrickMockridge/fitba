"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SeasonSelect } from "@/components/SeasonSelect";
import { formatDate } from "@/lib/format";
import type { FixtureIndexRow } from "@/lib/data";

function resultLabel(row: FixtureIndexRow) {
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

export function MatchRecordArchive({
  seasons,
  current,
}: {
  seasons: Array<{ season: string; rows: FixtureIndexRow[] }>;
  current: string;
}) {
  const [selected, setSelected] = useState(current);
  // Preserve the old `#season-YYYY-YY` deep links without making them the
  // default: the present season is what a plain visit shows.
  useEffect(() => {
    const match = window.location.hash.match(/^#season-(.+)$/);
    if (!match) return;
    const hashSeason = decodeURIComponent(match[1]);
    if (seasons.some((group) => group.season === hashSeason)) {
      setSelected(hashSeason);
    }
  }, [seasons]);

  const active = seasons.find((group) => group.season === selected) ?? seasons[0];
  if (!active) return null;

  function choose(season: string) {
    setSelected(season);
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#season-${season}`);
    }
  }

  return (
    <>
      <SeasonSelect
        seasons={seasons.map((group) => group.season)}
        current={current}
        selected={active.season}
        onSelect={choose}
      />
      <section
        className="card"
        id={`season-${active.season}`}
        data-contract="matches.season"
      >
        <div className="section-head">
          <div>
            <p className="eyebrow">{active.season}</p>
            <h2>{active.rows.length} played fixtures</h2>
          </div>
          {active.season === current ? (
            <span className="badge badge-ok">Current season</span>
          ) : null}
        </div>
        <div className="table-wrap">
          <table className="league-table">
            <caption className="fine-print">
              {active.season}: {active.rows.length} played fixtures. Depth is the
              highest record class available; the match page lists every class.
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
              {active.rows.map((row) => (
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
    </>
  );
}
