import type { FixtureDocument } from "@/lib/data";
import { formatDate } from "@/lib/format";

const DEPTH_LABELS: Record<string, string> = {
  full: "Full record",
  result: "Result, events and lineups",
  partial: "Partial record",
  score: "Score only",
};

export function MatchHeader({ fixture }: { fixture: FixtureDocument }) {
  const f = fixture.fixture;
  const hasShootout =
    f.home_penalties !== null && f.away_penalties !== null && f.home_penalties !== f.away_penalties;
  const aberdeenIsHome = f.home_team_id === "sco:aberdeen";
  const aberdeenPens = hasShootout
    ? aberdeenIsHome
      ? (f.home_penalties as number)
      : (f.away_penalties as number)
    : null;
  const opponentPens = hasShootout
    ? aberdeenIsHome
      ? (f.away_penalties as number)
      : (f.home_penalties as number)
    : null;
  const wonShootout =
    aberdeenPens !== null && opponentPens !== null ? aberdeenPens > opponentPens : null;
  const penaltyScore =
    aberdeenPens !== null && opponentPens !== null
      ? wonShootout
        ? `${aberdeenPens}–${opponentPens}`
        : `${opponentPens}–${aberdeenPens}`
      : null;
  const penaltyNote =
    penaltyScore !== null
      ? `Aberdeen ${wonShootout ? "won" : "lost"} ${penaltyScore} on penalties`
      : null;
  const score =
    f.home_goals === null || f.away_goals === null
      ? "Result unavailable"
      : `${f.home_team_name} ${f.home_goals}–${f.away_goals} ${f.away_team_name}${
          penaltyNote ? ` (${penaltyNote})` : ""
        }`;
  const resultClass =
    wonShootout === true || (!hasShootout && f.aberdeen_result === "W")
      ? "badge-positive"
      : wonShootout === false || (!hasShootout && f.aberdeen_result === "L")
        ? "badge-negative"
        : "badge-neutral";
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
        <span className={`badge ${resultClass}`}>
          {hasShootout && penaltyNote
            ? `Aberdeen ${f.aberdeen_result} · ${penaltyNote.replace("Aberdeen ", "")}`
            : `Aberdeen ${f.aberdeen_result}`}
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
