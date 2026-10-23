import Link from "next/link";
import type { ScoutingArchetypeDefinition, ScoutingPivot } from "@/lib/data";
import { formatDecimal, formatInteger } from "@/lib/format";

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
  goals_assists_p90: "Goals + assists /90",
  shots_p90: "Shots /90",
  conversion_pct: "Conversion",
  save_pct: "Save %",
  conceded_p90: "Goals conceded /90",
};

function featureList(features: Record<string, number>): string {
  return Object.entries(features)
    .map(([key, weight]) => `${FEATURE_LABELS[key] ?? key} ${formatDecimal(weight, 2)}`)
    .join(" · ");
}

function leaderList(leaders: ScoutingArchetypeDefinition["leaders"]) {
  if (!leaders.length) {
    return <p className="muted">No qualifying profile in the pool at the minutes threshold.</p>;
  }
  return (
    <ul className="plain-list">
      {leaders.map((leader) => (
        <li key={`${leader.player_id}-${leader.league_slug}`}>
          {leader.name} <span className="muted">· {leader.club} · {leader.league_name}</span>{" "}
          <span className="badge badge-neutral">
            adjusted {formatDecimal(leader.adjusted_score ?? 0, 1)}
          </span>{" "}
          <span className="muted">
            raw {formatDecimal(leader.raw_score ?? 0, 1)} · {formatInteger(leader.minutes)} mins
          </span>
          {leader.value_index !== null ? (
            <span className="muted"> · value index {formatDecimal(leader.value_index, 1)}</span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function pivotSide(
  id: string,
  label: string,
  current: ScoutingPivot["current"][string],
  leaders: ScoutingPivot["pool"][string],
) {
  return (
    <section className="mini-block">
      <h3>{label}</h3>
      <p className="fine-print">
        Current squad:{" "}
        {current
          ? `${current.name} · ${formatDecimal(current.score, 1)} (${formatInteger(current.minutes)} mins)`
          : "no qualifying profile at the minutes threshold"}
      </p>
      <p className="eyebrow">All-league profiles</p>
      {leaderList(leaders ?? [])}
      <Link className="text-link" href={`/scouting/search/#${id}`}>
        Filter the full search →
      </Link>
    </section>
  );
}

export function ScoutingArchetypes({
  archetypes,
  pivot,
}: {
  archetypes: ScoutingArchetypeDefinition[];
  pivot: ScoutingPivot | null;
}) {
  return (
    <>
      <p className="fine-print">
        Leaders are ranked by a league-adjusted profile score: the raw within-league score is
        mapped into the actual Premiership role distribution using the observed league level and
        spread. It is an empirical alignment, not a measured equivalence; the raw score is shown
        beside it. The value index is a scouting ordering, not a transfer value.
      </p>
      <div className="grid three-col">
        {archetypes.map((archetype) => (
          <section className="card" key={archetype.id}>
            <p className="eyebrow">Profile</p>
            <h3>{archetype.label}</h3>
            <p>{archetype.description}</p>
            <p className="fine-print">{featureList(archetype.features)}</p>
            <p className="eyebrow">All-league leaders</p>
            {leaderList(archetype.leaders)}
            <Link
              className="text-link"
              href={`/scouting/search/#${archetype.id}`}
            >
              Open this profile in the full search →
            </Link>
          </section>
        ))}
      </div>
      {pivot ? (
        <section className="card" data-contract="scouting.pivot">
          <div className="card-head">
            <div>
              <p className="eyebrow">The double pivot</p>
              <h2>Shield and a short forward pass</h2>
            </div>
            <span className="badge badge-warn">Hypothesis</span>
          </div>
          <div className="grid two-col">
            {pivotSide(
              "ball_winning_pivot",
              pivot.archetype_labels.ball_winning_pivot ?? "Ball-winning pivot",
              pivot.current.ball_winning_pivot,
              pivot.pool.ball_winning_pivot,
            )}
            {pivotSide(
              "deep_lying_playmaker",
              pivot.archetype_labels.deep_lying_playmaker ?? "Deep-lying playmaker",
              pivot.current.deep_lying_playmaker,
              pivot.pool.deep_lying_playmaker,
            )}
          </div>
          <p className="fine-print">{pivot.hypothesis}</p>
        </section>
      ) : null}
    </>
  );
}
