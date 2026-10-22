import Link from "next/link";
import type { CupFixture, CupRound as CupRoundType } from "@/lib/data";
import { formatDate } from "@/lib/data";

function TeamName({ fixture, side }: { fixture: CupFixture; side: "home" | "away" }) {
  const id = side === "home" ? fixture.home_team_id : fixture.away_team_id;
  const name = side === "home" ? fixture.home_team_name : fixture.away_team_name;
  const winner = fixture.winner_team_id === id;
  const content =
    id === "sco:aberdeen" ? <Link href="/matchday/">{name}</Link> : name;
  return <span className={winner ? "tie-winner" : undefined}>{content}</span>;
}

function Score({ fixture }: { fixture: CupFixture }) {
  if (fixture.home_goals !== null && fixture.away_goals !== null) {
    return (
      <span className="tie-score">
        <strong>
          {fixture.home_goals}–{fixture.away_goals}
        </strong>
        {fixture.home_penalties !== null && fixture.away_penalties !== null ? (
          <span className="pens">
            pens {fixture.home_penalties}–{fixture.away_penalties}
          </span>
        ) : fixture.extra_time ? (
          <span className="pens">AET</span>
        ) : null}
      </span>
    );
  }
  return <span className="tie-score muted">{fixture.kickoff ?? "TBC"}</span>;
}

export function CupRound({
  round,
  highlightTeamId,
}: {
  round: CupRoundType;
  highlightTeamId?: string;
}) {
  const hasFixtures = round.fixtures.length > 0;
  const coverageLabel =
    round.covered === false
      ? "Not in licensed feed"
      : hasFixtures
        ? `${round.fixtures.length} ties`
        : "TBC";

  return (
    <section className={`cup-round ${round.covered === false ? "is-uncovered" : ""}`}>
      <div className="section-head">
        <div>
          <p className="eyebrow">
            Round {round.order}
            {round.official_ties ? ` · ${round.official_ties} ties` : ""}
          </p>
          <h3>{round.name}</h3>
        </div>
        <span className={round.covered === false ? "badge badge-warn" : "badge badge-neutral"}>
          {coverageLabel}
        </span>
      </div>

      {round.note ? <p className="fine-print">{round.note}</p> : null}

      {hasFixtures ? (
        <div className="table-wrap">
          <table className="league-table compact cup-ties">
            <thead>
              <tr>
                <th>Date</th>
                <th>Home</th>
                <th className="num">Score</th>
                <th>Away</th>
              </tr>
            </thead>
            <tbody>
              {round.fixtures.map((fixture) => (
                <tr
                  key={fixture.match_id}
                  className={
                    fixture.home_team_id === highlightTeamId ||
                    fixture.away_team_id === highlightTeamId
                      ? "is-highlight"
                      : undefined
                  }
                >
                  <td>{formatDate(fixture.date)}</td>
                  <td>
                    <TeamName fixture={fixture} side="home" />
                  </td>
                  <td className="num">
                    <Score fixture={fixture} />
                  </td>
                  <td>
                    <TeamName fixture={fixture} side="away" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">
          {round.covered === false
            ? "The licensed feed does not provide this round. No ties are shown."
            : "No fixtures published yet."}
        </p>
      )}
    </section>
  );
}
