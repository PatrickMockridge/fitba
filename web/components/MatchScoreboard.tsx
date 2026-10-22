import type { FixtureDocument, FixtureScoreboardSide } from "@/lib/data";

const ABERDEEN_ID = "sco:aberdeen";

function minuteLabel(minute: number | null, extra: number | null): string {
  if (minute === null) return "Time unknown";
  return extra ? `${minute}+${extra}'` : `${minute}'`;
}

function statusLabel(status: string): string {
  if (status === "FT") return "Full time";
  if (status === "AET") return "After extra time";
  if (status === "PEN") return "Penalties";
  return status || "Played";
}

function sideLabel(side: FixtureScoreboardSide): string {
  return side.is_aberdeen ? "Aberdeen" : "Opposition";
}

function sideTeam(side: FixtureScoreboardSide): string {
  return side.is_aberdeen ? "aberdeen" : "opponent";
}

function ScoreboardSide({
  side,
  score,
  shootout,
  eventsAvailable,
  goalsComplete,
}: {
  side: FixtureScoreboardSide;
  score: number | null;
  shootout: { home: number; away: number } | null;
  eventsAvailable: boolean;
  goalsComplete: boolean;
}) {
  return (
    <section
      className={`scoreboard-side${side.is_aberdeen ? " is-aberdeen" : ""}`}
      data-contract="match.scoreboard.side"
      data-team={sideTeam(side)}
      aria-label={`${side.team_name}, ${side.side}`}
    >
      <div className="scoreboard-side-head">
        <p className="eyebrow">
          {side.side === "home" ? "Home" : "Away"} · {sideLabel(side)}
        </p>
        <h3>{side.team_name}</h3>
        <p className="scoreboard-score">{score ?? "—"}</p>
        {shootout ? (
          <p className="fine-print">
            Penalties {side.side === "home" ? shootout.home : shootout.away}
          </p>
        ) : null}
      </div>

      <h4>Goals</h4>
      {side.goals.length ? (
        <ul className="scoreboard-events">
          {side.goals.map((goal, index) => (
            <li className="scoreboard-event" key={`${goal.side}-goal-${index}`}>
              <span className="scoreboard-time">
                {minuteLabel(goal.minute, goal.extra_minute)}
              </span>
              <span>
                {goal.player_name ?? "Scorer unknown"}
                {goal.is_penalty ? <span className="badge badge-neutral">Penalty</span> : null}
                {goal.is_own_goal ? <span className="badge badge-warn">Own goal</span> : null}
                <span className="scoreboard-assist">
                  {goal.assist_name ? `Assist: ${goal.assist_name}` : "Assist not recorded"}
                </span>
                <span className="scoreboard-running">
                  {goal.score_after.home}–{goal.score_after.away}
                </span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="fine-print">
          {!eventsAvailable
            ? "Goal events unavailable."
            : goalsComplete
              ? "No goals."
              : "No recorded goals; the event feed is incomplete."}
        </p>
      )}

      <h4>Red cards</h4>
      {side.red_cards.length ? (
        <ul className="scoreboard-events">
          {side.red_cards.map((card, index) => (
            <li className="scoreboard-event" key={`${card.side}-red-${index}`}>
              <span className="scoreboard-time">
                {minuteLabel(card.minute, card.extra_minute)}
              </span>
              <span>
                {card.player_name ?? "Player unknown"}
                <span className="badge badge-negative">
                  {card.card_type === "second_yellow" ? "Second yellow" : "Straight red"}
                </span>
                {card.detail ? <span className="scoreboard-assist">{card.detail}</span> : null}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="fine-print">
          {eventsAvailable ? "No red cards in the event feed." : "Red-card events unavailable."}
        </p>
      )}
    </section>
  );
}

export function MatchScoreboard({ fixture }: { fixture: FixtureDocument }) {
  const f = fixture.fixture;
  const board = fixture.scoreboard;
  const home = board.home;
  const away = board.away;
  const opponent = f.home_team_id === ABERDEEN_ID ? f.away_team_name : f.home_team_name;
  return (
    <section
      className="card match-scoreboard"
      data-contract="match.scoreboard"
      data-team-split="aberdeen-opponent"
      aria-label={`${f.home_team_name} ${f.home_goals ?? "—"}–${f.away_goals ?? "—"} ${f.away_team_name} scoreboard`}
    >
      <div className="section-head">
        <div>
          <p className="eyebrow">Scoreboard</p>
          <h2>{f.competition_name}</h2>
        </div>
        <span className="badge badge-neutral">{statusLabel(f.status)}</span>
      </div>

      <div className="match-team-key" data-contract="match.team-key">
        <span className="team-key team-key-aberdeen">
          <span className="team-key-swatch" aria-hidden="true" />
          Aberdeen
        </span>
        <span className="team-key team-key-opponent">
          <span className="team-key-swatch" aria-hidden="true" />
          {opponent}
        </span>
        <span className="fine-print">
          Aberdeen is red throughout; the opposition is neutral.
        </span>
      </div>

      <div className="match-scoreboard-grid">
        <ScoreboardSide
          side={home}
          score={f.home_goals}
          shootout={board.shootout}
          eventsAvailable={board.events_available}
          goalsComplete={board.goals_complete}
        />
        <ScoreboardSide
          side={away}
          score={f.away_goals}
          shootout={board.shootout}
          eventsAvailable={board.events_available}
          goalsComplete={board.goals_complete}
        />
      </div>
      <p className="fine-print">{board.note}</p>
    </section>
  );
}
