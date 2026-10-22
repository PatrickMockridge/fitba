import type { ClubCompetition } from "@/lib/data";
import { formatDate } from "@/lib/data";

export function CompetitionStrip({ competitions }: { competitions: ClubCompetition[] }) {
  return (
    <div className="comp-strip">
      {competitions.map((competition) => {
        const active = competition.status === "Active";
        return (
          <div className="comp-card" key={competition.id}>
            <div className="comp-card-head">
              <span className="comp-name">{competition.short_name}</span>
              <span className={active ? "badge badge-ok" : "badge badge-warn"}>
                {competition.stage ?? competition.status}
              </span>
            </div>
            {competition.next_fixture ? (
              <span className="comp-next">
                {competition.next_fixture.venue === "H" ? "v" : "at"}{" "}
                {competition.next_fixture.opponent_name} ·{" "}
                {formatDate(competition.next_fixture.date)}
              </span>
            ) : competition.entry_round && competition.entry_date ? (
              <span className="comp-next">
                {competition.entry_round} · {formatDate(competition.entry_date)}
              </span>
            ) : (
              <span className="comp-next muted">{competition.note ?? "No fixture scheduled"}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
