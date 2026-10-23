import type { ClubFixture } from "@/lib/data";
import { formatDate } from "@/lib/data";

const COMPETITION_LABEL: Record<string, string> = {
  "sco:premiership": "League",
  "sco:championship": "League",
  "sco:league-one": "League",
  "sco:league-two": "League",
  "sco:league-cup": "League Cup",
  "sco:scottish-cup": "Scottish Cup",
};

export function FixtureList({
  fixtures,
  showResult = false,
  empty = "No fixtures scheduled.",
}: {
  fixtures: ClubFixture[];
  showResult?: boolean;
  empty?: string;
}) {
  if (!fixtures.length) return <p className="muted">{empty}</p>;
  return (
    <ul className="match-list fixture-list">
      {fixtures.map((fixture) => (
        <li key={fixture.match_id}>
          <span className="match-date">{formatDate(fixture.date)}</span>
          <span className="fixture-comp">
            {COMPETITION_LABEL[fixture.competition_id] ?? fixture.competition_name}
          </span>
          <span className="match-venue">{fixture.venue === "N" ? "Neutral" : fixture.venue}</span>
          <span className="match-opponent">
            {fixture.opponent_name}
            {fixture.stage ? <span className="stage-badge">{fixture.stage}</span> : null}
          </span>
          {showResult && fixture.result ? (
            <>
              <span className={`result-dot result-${fixture.result.toLowerCase()}`}>
                {fixture.result}
              </span>
              <span className="match-score">
                {fixture.goals_for}–{fixture.goals_against}
              </span>
            </>
          ) : (
            <span className="match-score muted">{fixture.kickoff ?? "TBC"}</span>
          )}
        </li>
      ))}
    </ul>
  );
}
