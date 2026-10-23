import Link from "next/link";
import type {
  ScoutingArchetypeDefinition,
  ScoutingLeader,
  ScoutingPriorityConfig,
} from "@/lib/data";
import { formatDecimal, formatInteger, formatSigned } from "@/lib/format";

const FEATURE_LABELS: Record<string, string> = {
  tackles_p90: "Tackles /90",
  interceptions_p90: "Interceptions /90",
  duel_win_pct: "Duels won %",
  pass_completion_pct: "Pass completion",
  passes_completed_p90: "Completed passes /90",
  key_passes_p90: "Key passes /90",
  assists_p90: "Assists /90",
  dribbles_success_p90: "Successful dribbles /90",
  dribble_success_pct: "Dribble success",
  goals_p90: "Goals /90",
  goals_assists_p90: "Goals + assists /90",
  shots_p90: "Shots /90",
  conversion_pct: "Conversion",
  save_pct: "Save %",
  conceded_p90: "Goals conceded /90",
};

const EUROPE_LABELS: Record<string, string> = {
  "UEFA Champions League": "UCL",
  "UEFA Europa League": "UEL",
  "UEFA Conference League": "UECL",
};

function featureList(features: Record<string, number>): string {
  return Object.entries(features)
    .map(([key, weight]) => `${FEATURE_LABELS[key] ?? key} ${formatDecimal(weight, 2)}`)
    .join(" · ");
}

export function leaderList(
  leaders: ScoutingLeader[],
  weights: ScoutingPriorityConfig,
) {
  if (!leaders.length) {
    return <p className="muted">No qualifying profile in the pool at the minutes threshold.</p>;
  }
  return (
    <ul className="plain-list">
      {leaders.map((leader) => (
        <li key={`${leader.player_id}-${leader.league_slug}`}>
          <Link href={`/scouting/player/${leader.player_id}/`}>{leader.name}</Link>{" "}
          <span className="muted">
            · {leader.club}
            {leader.stats_club && leader.stats_club !== leader.club
              ? ` (stats at ${leader.stats_club})`
              : ""}{" "}
            · {leader.league_name}
          </span>{" "}
          <span className="badge badge-neutral">
            priority {formatDecimal(leader.scouting_priority ?? 0, 1)}
          </span>{" "}
          {leader.bias !== undefined && leader.bias !== null ? (
            <span className="badge badge-neutral">
              bias {formatSigned(leader.bias, 1)}
            </span>
          ) : null}{" "}
          <span className="muted">
            adjusted {formatDecimal(leader.adjusted_score ?? 0, 1)} · raw{" "}
            {formatDecimal(leader.raw_score ?? 0, 1)} · {formatInteger(leader.minutes)} mins
          </span>
          {leader.age !== null && leader.age <= weights.u23_max_age ? (
            <span className="badge badge-neutral"> U23</span>
          ) : null}
          {leader.european_status === "qualified" ? (
            <span className="badge badge-warn">
              {" "}
              {leader.european_league_phase_competitions
                .map((name) => EUROPE_LABELS[name] ?? name)
                .join("/")}{" "}
              · {formatInteger(leader.european_league_phase_minutes ?? 0)}m
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export function ScoutingArchetypes({
  archetypes,
  priority,
}: {
  archetypes: ScoutingArchetypeDefinition[];
  priority: ScoutingPriorityConfig;
}) {
  return (
    <>
      <p className="fine-print" data-contract-indicator="basis">
        Leaders are filtered for the profile and its coverage, then ordered by the profile score
        with the Aberdeen preferences applied: adjusted profile × U23 multiplier × European
        league-phase multiplier. U23 ≤{formatInteger(priority.u23_max_age)} ×
        {formatDecimal(priority.u23_multiplier, 2)}; European league phase ≥
        {formatInteger(priority.europe_minutes_threshold)} min ×
        {formatDecimal(priority.europe_multiplier, 2)}. Ranking by the value-index priority
        alone put the same players at the top of every attacking profile. These are preferences,
        not measured quality. The raw and adjusted profile scores are shown beside the priority.
      </p>
      <div className="grid three-col">
        {archetypes.map((archetype) => (
          <section className="card" key={archetype.id}>
            <p className="eyebrow">Profile</p>
            <h3>{archetype.label}</h3>
            <p>{archetype.description}</p>
            <p className="fine-print">{featureList(archetype.features)}</p>
            <p className="eyebrow">All-league priority leaders</p>
            {leaderList(archetype.leaders, priority)}
            <Link className="text-link" href={`/scouting/search/#${archetype.id}`}>
              Open this profile in the full search →
            </Link>
          </section>
        ))}
      </div>
    </>
  );
}
