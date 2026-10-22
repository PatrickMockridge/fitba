import type { FixtureDocument } from "@/lib/data";

function minute(row: FixtureDocument["timeline"][number]): string {
  if (row.minute === null) return "—";
  return row.extra_minute ? `${row.minute}+${row.extra_minute}'` : `${row.minute}'`;
}

function label(row: FixtureDocument["timeline"][number]): string {
  if (row.is_goal) {
    if (row.is_own_goal) return "Own goal";
    if (row.is_penalty) return "Penalty";
    if (row.is_shootout) return "Shootout goal";
    return "Goal";
  }
  if (row.is_red_card) return "Red card";
  if (row.event_type === "Card") return "Card";
  if (row.event_type === "subst") return "Substitution";
  if (row.is_var) return "VAR";
  return row.event_type ?? "Event";
}

export function MatchTimeline({ timeline }: { timeline: FixtureDocument["timeline"] }) {
  return (
    <section className="card" data-contract="match.timeline">
      <div className="section-head">
        <div>
          <p className="eyebrow">Timeline</p>
          <h2>The match record</h2>
        </div>
      </div>
      {timeline.length ? (
        <div className="table-wrap">
          <table className="league-table">
            <thead>
              <tr>
                <th>Min</th>
                <th>Event</th>
                <th>Team</th>
                <th>Player</th>
                <th>Detail</th>
                <th className="num">Score</th>
              </tr>
            </thead>
            <tbody>
              {timeline.map((row, index) => (
                <tr key={index}>
                  <td className="num">{minute(row)}</td>
                  <td>{label(row)}</td>
                  <td>{row.team_name ?? "—"}</td>
                  <td>{row.player_name ?? "—"}</td>
                  <td>{row.detail ?? (row.is_var ? "VAR" : "—")}</td>
                  <td className="num">
                    {row.is_goal ? `${row.score_after.home}–${row.score_after.away}` : "—"}
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
