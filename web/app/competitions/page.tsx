import Link from "next/link";
import { formatDate, getCompetitionIndex } from "@/lib/data";

export const metadata = { title: "Competitions · fitba" };

export default function CompetitionsPage() {
  const index = getCompetitionIndex();
  if (!index) {
    return (
      <section className="empty-state">
        <h1>No competitions published</h1>
        <p>Run <code>uv run fitba cups</code> and <code>uv run fitba publish</code>.</p>
      </section>
    );
  }
  const competitions = index.competitions.filter(
    (competition) =>
      competition.aberdeen_involved && competition.season === index.season,
  );

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Aberdeen · Season {index.season}</p>
        <h1>Competitions</h1>
        <p className="lede">
          The competitions Aberdeen are competing in this season, with the
          current stage and next fixture. The full Scottish pyramid remains
          available separately.
        </p>
        <div className="hero-actions">
          <Link className="button button-ghost" href="/sources/">
            Sources &amp; licences
          </Link>
          <Link className="button button-ghost" href="/scotland/">
            Full pyramid
          </Link>
        </div>
      </section>

      <div className="grid two-col">
        {competitions.map((competition) => {
          if (competition.kind === "league") {
            return (
              <Link className="card tier-card" key={competition.id} href={competition.link}>
                <div className="card-head">
                  <div>
                    <p className="eyebrow">Tier {competition.tier} · League</p>
                    <h2>{competition.name}</h2>
                  </div>
                  <span className="badge badge-ok">League</span>
                </div>
                {competition.leader ? (
                  <ol className="mini-table">
                    <li>
                      <span className="mini-pos">1</span>
                      <span className="mini-team">{competition.leader.team_name}</span>
                      <span className="mini-pts">{competition.leader.points}</span>
                    </li>
                  </ol>
                ) : null}
                <span className="text-link">Open table →</span>
              </Link>
            );
          }
          const partial = competition.coverage === "partial";
          return (
            <Link className="card tier-card" key={competition.id} href={competition.link}>
              <div className="card-head">
                <div>
                  <p className="eyebrow">Cup · {competition.season}</p>
                  <h2>{competition.name}</h2>
                </div>
                <span className={partial ? "badge badge-warn" : "badge badge-ok"}>
                  {partial ? "Partial coverage" : "Cup"}
                </span>
              </div>
              <p>
                <strong>{competition.stage ?? competition.status}</strong>
                {competition.aberdeen_note
                  ? ` · ${competition.aberdeen_note}`
                  : competition.next_fixture
                    ? ` · ${competition.next_fixture.home_team_name} v ${
                        competition.next_fixture.away_team_name
                      } · ${formatDate(competition.next_fixture.date)}`
                    : ""}
              </p>
              <span className="text-link">Open competition →</span>
            </Link>
          );
        })}
      </div>

      {index.europe ? (
        <section className="card">
          <div className="card-head">
            <div>
              <p className="eyebrow">Europe</p>
              <h2>
                {index.europe.in_europe
                  ? "European competition"
                  : "Not applicable this season"}
              </h2>
            </div>
            <span className="badge badge-neutral">
              {index.europe.in_europe ? "In Europe" : "Not in Europe"}
            </span>
          </div>
          {index.europe.in_europe && index.europe.competitions.length ? (
            <ul className="plain-list">
              {index.europe.competitions.map((competition) => (
                <li key={competition.id}>
                  <strong>{competition.name}</strong>
                  {competition.stage ? ` · ${competition.stage}` : ""}
                  {competition.next_fixture
                    ? ` · ${competition.next_fixture.home_team_name} v ${
                        competition.next_fixture.away_team_name
                      } · ${formatDate(competition.next_fixture.date)}`
                    : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p>
              {index.europe.note ??
                "Aberdeen are not in a UEFA competition this season."}
            </p>
          )}
          <p className="fine-print">
            European entry is checked separately from the SPFL pyramid. A blank
            state means not qualified, not missing data.
          </p>
        </section>
      ) : null}

      <p className="fine-print">
        Premiership and League Cup data comes from the licensed API-Football
        feed. The Scottish Cup feed is partial: 50 of 136 ties at the last check,
        with the preliminary rounds not provided. Every cup page labels what it
        has and what it does not.
      </p>
    </>
  );
}
