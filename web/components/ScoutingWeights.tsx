import Link from "next/link";
import type {
  ScoutingEuropeCoverage,
  ScoutingPriorityConfig,
} from "@/lib/data";
import { formatDecimal, formatInteger } from "@/lib/format";

export function ScoutingWeightsCard({
  priority,
  europe,
}: {
  priority: ScoutingPriorityConfig;
  europe: ScoutingEuropeCoverage | null;
}) {
  const competitions = europe?.competitions ?? [];
  const asked = competitions.reduce((sum, item) => sum + (item.played ?? 0), 0);
  const fetched = competitions.reduce((sum, item) => sum + (item.fetched ?? 0), 0);
  return (
    <>
      <div className="card-head">
        <div>
          <p className="eyebrow">Scouting weights</p>
          <h2>Youth and the European shop window</h2>
        </div>
        <span className="badge badge-neutral">Preference, not measured quality</span>
      </div>
      <p data-contract-indicator="basis">
        The value index is unchanged. A separate scouting priority applies two Aberdeen
        preferences: U23 players are weighted more strongly, and players who have already had a
        Champions League, Europa League or Conference League league-phase shop window are
        weighted less strongly.
      </p>
      <div className="stat-row four">
        <div className="stat-tile">
          <span className="stat-label">U23 cutoff</span>
          <span className="stat-value">≤ {formatInteger(priority.u23_max_age)}</span>
          <span className="stat-note">age on the scouting date</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">U23 multiplier</span>
          <span className="stat-value">×{formatDecimal(priority.u23_multiplier, 2)}</span>
          <span className="stat-note">applied to the value index</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Europe threshold</span>
          <span className="stat-value">
            {formatInteger(priority.europe_minutes_threshold)} min
          </span>
          <span className="stat-note">league-phase minutes</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Europe multiplier</span>
          <span className="stat-value">×{formatDecimal(priority.europe_multiplier, 2)}</span>
          <span className="stat-note">shop-window discount</span>
        </div>
      </div>
      <p className="fine-print">
        Priority = value index × U23 multiplier × European league-phase multiplier. Players
        below the 90-minute threshold are shown but not discounted; unknown European status is
        not discounted and is never treated as “not in Europe”. The value index remains a
        scouting ordering, not a transfer value.
      </p>
      <p className="fine-print">
        European league-phase coverage:{" "}
        {europe?.coverage_complete ? "complete" : "partial or unavailable"} ·{" "}
        {formatInteger(fetched)}/{formatInteger(asked)} played league-phase fixtures fetched ·{" "}
        {formatInteger(competitions.length)} competitions.{" "}
        {competitions.map((item) => (
          <span key={item.competition_id}>
            {item.competition} {formatInteger(item.fetched)}/{formatInteger(item.played)};{" "}
          </span>
        ))}
        {europe ? (
          <span>
            {formatInteger(europe.players ?? 0)} players with league-phase minutes; coverage is{" "}
            {europe.coverage_complete ? "complete" : "partial"}.
          </span>
        ) : (
          <span>No European league-phase snapshot is published.</span>
        )}
      </p>
      <p className="fine-print">
        See <Link href="/methodology/">the method</Link> and{" "}
        <Link href="/sources/">sources and licences</Link>. The European flag is separate from
        the domestic player pool.
      </p>
    </>
  );
}
