import type { ThemePillar } from "@/lib/data";

interface MissionMetrics {
  pillars?: ThemePillar[];
  recruitment?: {
    arrivals?: number;
    departures?: number;
    median_age?: number | null;
    permanent_in?: number;
    permanent_out?: number;
    loans_out?: number;
    disclosed_count?: number;
  };
  selection?: {
    players_used?: number | null;
    u21_minutes_share?: number | null;
    formation_mix?: Array<{ formation: string; fixtures: number; share: number }>;
  };
  scorecard?: {
    best_position?: number | null;
    worst_position?: number | null;
    manager_count?: number | null;
    honours_total?: number | null;
  };
  defensive_arrivals?: Array<{
    player_name?: string | null;
    from_club_name?: string | null;
    date_effective?: string | null;
    transfer_kind?: string | null;
  }>;
  commercial_context?: string | null;
}

export function MissionPanel({ metrics }: { metrics: MissionMetrics }) {
  const recruitment = metrics.recruitment ?? {};
  const selection = metrics.selection ?? {};
  const scorecard = metrics.scorecard ?? {};
  return (
    <div className="mission-panel">
      <div className="pillar-grid">
        {(metrics.pillars ?? []).map((pillar) => (
          <article className="pillar-card" key={pillar.id}>
            <p className="eyebrow">Mission pillar</p>
            <h4>{pillar.title}</h4>
            <p>{pillar.statement}</p>
            <p className="fine-print">Curated framing, not an audited club plan.</p>
          </article>
        ))}
      </div>
      <div className="stat-row four">
        <div className="stat-tile">
          <span className="stat-label">2026-27 arrivals</span>
          <span className="stat-value">{recruitment.arrivals ?? "—"}</span>
          <span className="stat-note">{recruitment.departures ?? "—"} departures</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Median arrival age</span>
          <span className="stat-value">{recruitment.median_age ?? "—"}</span>
          <span className="stat-note">current rebuild</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">U21 minutes</span>
          <span className="stat-value">
            {selection.u21_minutes_share === null || selection.u21_minutes_share === undefined
              ? "—"
              : `${Math.round(selection.u21_minutes_share * 100)}%`}
          </span>
          <span className="stat-note">{selection.players_used ?? "—"} players used</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Era league range</span>
          <span className="stat-value">
            {scorecard.best_position ?? "—"}–{scorecard.worst_position ?? "—"}
          </span>
          <span className="stat-note">
            {scorecard.manager_count ?? "—"} manager spells ·{" "}
            {scorecard.honours_total ?? "—"} honours
          </span>
        </div>
      </div>
      {metrics.defensive_arrivals?.length ? (
        <div className="table-wrap">
          <table className="league-table compact">
            <thead>
              <tr>
                <th>Defensive arrival</th>
                <th>From</th>
                <th>Date</th>
                <th>Kind</th>
              </tr>
            </thead>
            <tbody>
              {metrics.defensive_arrivals.map((player) => (
                <tr key={`${player.player_name}-${player.date_effective}`}>
                  <td className="strong">{player.player_name ?? "Unknown"}</td>
                  <td>{player.from_club_name ?? "—"}</td>
                  <td>{player.date_effective ?? "—"}</td>
                  <td>{player.transfer_kind ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {metrics.commercial_context ? (
        <p className="fine-print">{metrics.commercial_context}</p>
      ) : null}
    </div>
  );
}
