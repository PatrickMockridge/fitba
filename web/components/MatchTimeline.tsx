import type { FixtureDocument } from "@/lib/data";

function minute(row: FixtureDocument["timeline"][number]): string {
  if (row.minute === null) return "—";
  return row.extra_minute ? `${row.minute}+${row.extra_minute}'` : `${row.minute}'`;
}

function label(row: FixtureDocument["timeline"][number]): string {
  if (row.is_shootout) {
    return row.is_goal ? "Shootout goal" : "Shootout penalty missed";
  }
  if (row.is_goal) {
    if (row.is_own_goal) return "Own goal";
    if (row.is_penalty) return "Penalty";
    return "Goal";
  }
  if (row.is_missed_penalty) return "Missed penalty";
  if (row.card_type === "second_yellow") return "Second yellow";
  if (row.card_type === "straight_red") return "Straight red";
  if (row.event_type === "card") return "Yellow card";
  if (row.event_type === "subst") return "Substitution";
  if (row.is_var) return "VAR";
  return row.event_type ?? "Event";
}

function teamAttr(
  row: FixtureDocument["timeline"][number],
  aberdeenIsHome: boolean,
): string {
  if (!row.side) return "unknown";
  return (row.side === "home") === aberdeenIsHome ? "aberdeen" : "opponent";
}

export function MatchTimeline({
  timeline,
  aberdeenIsHome,
}: {
  timeline: FixtureDocument["timeline"];
  aberdeenIsHome: boolean;
}) {
  return (
    <section
      className="card match-timeline"
      data-contract="match.timeline"
      data-team-split="aberdeen-opponent"
    >
      <div className="section-head">
        <div>
          <p className="eyebrow">Timeline</p>
          <h2>The match record</h2>
        </div>
      </div>
      {timeline.length ? (
        <div className="table-wrap">
          <table className="league-table">
            <caption className="fine-print">
              Match timeline with Aberdeen highlighted in red.
            </caption>
            <thead>
              <tr>
                <th scope="col">Min</th>
                <th scope="col">Event</th>
                <th scope="col">Team</th>
                <th scope="col">Player</th>
                <th scope="col">Detail</th>
                <th scope="col" className="num">
                  Score
                </th>
              </tr>
            </thead>
            <tbody>
              {timeline.map((row, index) => (
                <tr key={index} data-team={teamAttr(row, aberdeenIsHome)}>
                  <td className="num">{minute(row)}</td>
                  <td>{label(row)}</td>
                  <td>{row.team_name ?? "—"}</td>
                  <td>{row.player_name ?? "—"}</td>
                  <td>{row.detail ?? (row.is_var ? "VAR" : "—")}</td>
                  <td className="num">
                    {row.is_goal && !row.is_shootout
                      ? `${row.score_after.home}–${row.score_after.away}`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="fine-print">
          The event feed is unavailable for this fixture. The score and the
          league record are shown.
        </p>
      )}
    </section>
  );
}
