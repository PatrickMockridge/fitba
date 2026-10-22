import type { FixtureDocument } from "@/lib/data";
import { formatDate } from "@/lib/format";

const DEPTH_LABELS: Record<string, string> = {
  full: "Full record",
  result: "Result, events and lineups",
  score: "Score only",
};

export function MatchHeader({ fixture }: { fixture: FixtureDocument }) {
  const f = fixture.fixture;
  const score =
    f.home_goals === null || f.away_goals === null
      ? "Result unavailable"
      : `${f.home_team_name} ${f.home_goals}–${f.away_goals} ${f.away_team_name}`;
  return (
    <section className="page-head match-head" data-contract="match.header">
      <p className="eyebrow">
        {f.competition_name}
        {f.round ? ` · ${f.round}` : ""}
      </p>
      <h1>{score}</h1>
      <p className="lede">
        {formatDate(f.date)}
        {f.venue_name ? ` · ${f.venue_name}` : ""}
        {f.referee ? ` · Referee: ${f.referee}` : ""}
      </p>
      <p className="match-meta">
        <span className={`badge ${f.aberdeen_result === "W" ? "badge-positive" : f.aberdeen_result === "L" ? "badge-negative" : "badge-neutral"}`}>
          Aberdeen {f.aberdeen_result}
        </span>
        <span className="badge badge-neutral">{f.status || "played"}</span>
        <span className="badge badge-neutral">{DEPTH_LABELS[fixture.depth] ?? fixture.depth}</span>
        {f.home_ht_goals !== null && f.away_ht_goals !== null ? (
          <span className="badge badge-neutral">
            Half-time {f.home_ht_goals}–{f.away_ht_goals}
          </span>
        ) : null}
        {f.home_penalties !== null && f.away_penalties !== null ? (
          <span className="badge badge-neutral">
            Penalties {f.home_penalties}–{f.away_penalties}
          </span>
        ) : null}
      </p>
    </section>
  );
}
