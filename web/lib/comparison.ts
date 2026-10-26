import type {
  ScoutingSearchMeta,
  ScoutingSearchRow,
  ScoutingSquadRow,
} from "@/lib/data";

export type ComparisonRate = {
  id: string;
  label: string;
  value: number | null;
  unit: "%" | "/90";
};

export type ComparisonArchetype = {
  id: string;
  label: string;
  score: number | null;
};

export type ComparisonPlayer = {
  key: string;
  playerId: number;
  name: string;
  href: string;
  source: "squad" | "scouted";
  leagueSlug: string;
  leagueLabel: string;
  roleFamily: string;
  roleLabel: string;
  minutes: number | null;
  rating: number | null;
  percentile: number | null;
  cohortBasis: string | null;
  cohortN: number | null;
  rates: ComparisonRate[];
  archetypes: ComparisonArchetype[];
  profile: string | null;
};

export type ComparisonGuard =
  | { comparable: true }
  | { comparable: false; reason: string };

const RATE_FIELDS: Array<{
  id: string;
  label: string;
  unit: "%" | "/90";
}> = [
  { id: "goals_assists", label: "Goals + assists", unit: "/90" },
  { id: "goals", label: "Goals", unit: "/90" },
  { id: "shots", label: "Shots", unit: "/90" },
  { id: "dribbles", label: "Dribbles won", unit: "/90" },
  { id: "passes", label: "Passes completed", unit: "/90" },
  { id: "pass_pct", label: "Pass completion", unit: "%" },
  { id: "key_passes", label: "Key passes", unit: "/90" },
  { id: "tackles", label: "Tackles", unit: "/90" },
  { id: "interceptions", label: "Interceptions", unit: "/90" },
  { id: "duels", label: "Duels won", unit: "%" },
];

function rateRow(
  values: Record<string, number | null>,
): ComparisonRate[] {
  return RATE_FIELDS.map((field) => ({
    id: field.id,
    label: field.label,
    unit: field.unit,
    value: values[field.id] ?? null,
  }));
}

export function fromSquadRow(row: ScoutingSquadRow): ComparisonPlayer {
  return {
    key: `squad-${row.player_id}`,
    playerId: row.player_id,
    name: row.name,
    href: `/players/${row.player_id}/`,
    source: "squad",
    leagueSlug: "sco-premiership",
    leagueLabel: "Scottish Premiership",
    roleFamily: row.role_family ?? "",
    roleLabel: row.role_label,
    minutes: row.minutes ?? null,
    rating: row.rating,
    percentile: row.rating_percentile,
    cohortBasis: row.cohort?.basis ?? null,
    cohortN: row.cohort?.n ?? null,
    rates: rateRow({
      goals_assists: row.goals_assists_p90,
      goals: row.goals_p90,
      shots: row.shots_p90,
      dribbles: row.dribbles_success_p90,
      passes: row.passes_completed_p90,
      pass_pct: row.pass_completion_pct,
      key_passes: row.key_passes_p90,
      tackles: row.tackles_p90,
      interceptions: row.interceptions_p90,
      duels: row.duel_win_pct,
    }),
    archetypes: Object.entries(row.archetypes ?? {}).map(([id, score]) => ({
      id,
      label: id.replaceAll("_", " "),
      score: score?.score ?? null,
    })),
    profile: row.profile?.id ?? null,
  };
}

export function fromSearchRow(
  row: ScoutingSearchRow,
  meta: ScoutingSearchMeta,
): ComparisonPlayer {
  const order = meta.profile_order ?? [];
  const labels = meta.profile_labels ?? {};
  return {
    key: `scouted-${row.i}`,
    playerId: row.i,
    name: row.n,
    href: `/scouting/player/${row.i}/`,
    source: "scouted",
    leagueSlug: row.l,
    leagueLabel: meta.leagues.find((league) => league.slug === row.l)?.name ?? row.l,
    roleFamily: row.rf ?? "",
    roleLabel: row.rf ? (meta.role_labels[row.rf] ?? row.rf) : "Role unknown",
    minutes: row.m ?? null,
    rating: row.rt,
    percentile: row.p,
    cohortBasis: row.cb ?? null,
    cohortN: row.cn ?? null,
    rates: rateRow({
      goals_assists: row.ga,
      goals: row.g90,
      shots: row.sh90,
      dribbles: row.dr,
      passes: row.ps,
      pass_pct: row.pa,
      key_passes: row.kp,
      tackles: row.tk,
      interceptions: row.it,
      duels: row.dw,
    }),
    archetypes: (row.arp ?? []).map(([index, adjusted, raw]) => ({
      id: order[index] ?? `profile-${index}`,
      label: labels[order[index]] ?? order[index] ?? `Profile ${index}`,
      score: adjusted ?? raw ?? null,
    })),
    profile: row.pr,
  };
}

export function comparisonGuard(
  left: ComparisonPlayer,
  right: ComparisonPlayer,
  meta: ScoutingSearchMeta,
): ComparisonGuard {
  if (!left.roleFamily || !right.roleFamily) {
    return { comparable: false, reason: "A role family is unknown for one of the players." };
  }
  if (left.leagueSlug !== right.leagueSlug) {
    return {
      comparable: false,
      reason: "The players are in different leagues; this panel never compares across leagues.",
    };
  }
  if (left.roleFamily !== right.roleFamily) {
    return {
      comparable: false,
      reason: "The players are in different role families; the cohort would not be like-for-like.",
    };
  }
  if (left.percentile === null || right.percentile === null) {
    return {
      comparable: false,
      reason: "One player has no published within-league percentile.",
    };
  }
  const minimum =
    meta.min_cohort_by_family?.[left.roleFamily] ?? meta.min_cohort ?? 15;
  if ((left.cohortN ?? 0) < minimum || (right.cohortN ?? 0) < minimum) {
    return {
      comparable: false,
      reason: `The role cohort is below the published minimum of ${minimum}.`,
    };
  }
  return { comparable: true };
}
