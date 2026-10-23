import type {
  ScoutingArchetypeDefinition,
  ScoutingAttackers,
  ScoutingGoalScorer,
  ScoutingLeader,
  ScoutingPriorityConfig,
  ScoutingSearchDocument,
  ScoutingSearchRow,
} from "@/lib/data";
import { roundHalfEven } from "@/lib/format";

export type ScoutingSortKey =
  | "priority"
  | "mix"
  | "league"
  | "percentile"
  | "adjusted"
  | "value_index"
  | "rating"
  | "minutes"
  | "goals_assists"
  | "archetype"
  | "team_lift";

export interface ScoutingLenses {
  priorityActive: boolean;
  u23Boost: boolean;
  u23Only: boolean;
  europeDiscount: boolean;
  excludeEurope: boolean;
  underperformingOnly: boolean;
  archetype: string;
  role: string;
  league: string;
}

export interface ScoutingFilters {
  query: string;
  nationality: string;
  minMinutes: number;
  maxAge: number | null;
  europeStatus: string;
  roleKnownOnly: boolean;
  minValueCoverage: number | null;
}

export interface ScoutingValueWeights {
  performance: number;
  age: number;
  minutes: number;
  profile: number;
}

export interface ScoutingPoolRow {
  player_id: number;
  name: string;
  club: string;
  stats_club: string;
  league_id: string;
  league_slug: string;
  league_name: string;
  nationality: string | null;
  role_family: string | null;
  role_label: string;
  age: number | null;
  minutes: number;
  rating: number | null;
  rating_percentile: number | null;
  adjusted_percentile: number | null;
  value_index: number | null;
  value_index_coverage: number | null;
  current_club_status: string | null;
  european_status: string;
  european_minutes: number | null;
  european_competitions: string[];
  goals: number | null;
  assists: number | null;
  goals_p90: number | null;
  assists_p90: number | null;
  goals_assists_p90: number | null;
  shots_p90: number | null;
  conversion_pct: number | null;
  team_rank: number | null;
  team_points: number | null;
  team_count: number | null;
  team_points_percentile: number | null;
  team_underperforming: boolean | null;
  team_lift: number | null;
  top_profile: string | null;
  top_profile_score: number | null;
  archetypes: Record<string, number | null>;
  profile_raw: Record<string, number | null>;
  profile_coverage: Record<string, number | null>;
  flags: string[];
}

export interface ScoutingSession {
  document: ScoutingSearchDocument;
  priority: ScoutingPriorityConfig;
  lenses: ScoutingLenses;
  filters: ScoutingFilters;
  valueWeights: ScoutingValueWeights;
  teamThreshold: number;
  minLift: number;
}

const EUROPE_NAMES: Record<string, string> = {
  ucl: "UEFA Champions League",
  uel: "UEFA Europa League",
  uecl: "UEFA Conference League",
};

const FLAG_NAMES: Record<string, string> = {
  l: "low_minutes",
  r: "role_unknown",
  n: "no_rating",
};

const ATTACK_FAMILIES = new Set([
  "centre_forward",
  "wide_forward",
  "attacking_midfield",
]);

export function defaultLenses(): ScoutingLenses {
  return {
    priorityActive: false,
    u23Boost: true,
    u23Only: false,
    europeDiscount: true,
    excludeEurope: false,
    underperformingOnly: false,
    archetype: "all",
    role: "all",
    league: "all",
  };
}

export function defaultFilters(minMinutes: number): ScoutingFilters {
  return {
    query: "",
    nationality: "all",
    minMinutes,
    maxAge: null,
    europeStatus: "any",
    roleKnownOnly: false,
    minValueCoverage: null,
  };
}

export function defaultValueWeights(
  document: ScoutingSearchDocument,
): ScoutingValueWeights {
  const weights = document.value_model.weights;
  return {
    performance: weights.performance ?? 0.55,
    age: weights.age ?? 0.15,
    minutes: weights.minutes ?? 0.15,
    profile: weights.profile ?? 0.15,
  };
}

export function isDefaultLenses(lenses: ScoutingLenses): boolean {
  return (
    !lenses.priorityActive &&
    lenses.u23Boost &&
    !lenses.u23Only &&
    lenses.europeDiscount &&
    !lenses.excludeEurope &&
    !lenses.underperformingOnly &&
    lenses.archetype === "all" &&
    lenses.role === "all" &&
    lenses.league === "all"
  );
}

export function isDefaultFilters(
  filters: ScoutingFilters,
  document: ScoutingSearchDocument,
): boolean {
  return (
    filters.query.trim() === "" &&
    filters.nationality === "all" &&
    filters.minMinutes === document.min_minutes &&
    filters.maxAge === null &&
    filters.europeStatus === "any" &&
    !filters.roleKnownOnly &&
    filters.minValueCoverage === null
  );
}

export function isDefaultValueWeights(
  weights: ScoutingValueWeights,
  document: ScoutingSearchDocument,
): boolean {
  const published = defaultValueWeights(document);
  return (Object.keys(published) as Array<keyof ScoutingValueWeights>).every(
    (key) => Math.abs(weights[key] - published[key]) < 1e-9,
  );
}

export function ageFactor(
  age: number | null,
  priority: ScoutingPriorityConfig,
  lenses: ScoutingLenses,
): number {
  return lenses.u23Boost && age !== null && age <= priority.u23_max_age
    ? priority.u23_multiplier
    : 1;
}

export function europeFactor(
  status: string,
  priority: ScoutingPriorityConfig,
  lenses: ScoutingLenses,
): number {
  return lenses.europeDiscount && status === "qualified"
    ? priority.europe_multiplier
    : 1;
}

export function priorityFor(
  valueIndex: number | null,
  age: number | null,
  status: string,
  priority: ScoutingPriorityConfig,
  lenses: ScoutingLenses,
): number | null {
  if (valueIndex === null) return null;
  return roundHalfEven(
    valueIndex * ageFactor(age, priority, lenses) * europeFactor(status, priority, lenses),
    1,
  );
}

export function profileRank(
  adjustedScore: number | null,
  age: number | null,
  status: string,
  priority: ScoutingPriorityConfig,
  lenses: ScoutingLenses,
): number | null {
  if (adjustedScore === null) return null;
  return (
    adjustedScore *
    ageFactor(age, priority, lenses) *
    europeFactor(status, priority, lenses)
  );
}

function ageCurve(
  age: number | null,
  bands: Array<{ max_age: number; factor: number }>,
): number | null {
  if (age === null) return null;
  for (const band of bands) {
    if (age <= band.max_age) return band.factor;
  }
  return bands.length ? bands[bands.length - 1].factor : 0.3;
}

export interface ValueIndexInput {
  adjusted_percentile: number | null;
  age: number | null;
  minutes: number;
  archetypes: Record<string, number | null>;
}

export function readerValueIndexFor(
  input: ValueIndexInput,
  weights: ScoutingValueWeights,
  valueModel: ScoutingSearchDocument["value_model"],
): number | null {
  const components: Partial<Record<keyof ScoutingValueWeights, number>> = {};
  if (input.adjusted_percentile !== null) {
    components.performance = input.adjusted_percentile / 100;
  }
  const age = ageCurve(input.age, valueModel.age_curve);
  if (age !== null) components.age = age;
  if (input.minutes > 0) {
    components.minutes = Math.min(1, input.minutes / valueModel.minutes_full);
  }
  const scores = Object.values(input.archetypes).filter(
    (value): value is number => value !== null,
  );
  if (scores.length) components.profile = Math.max(...scores) / 100;

  const total =
    weights.performance + weights.age + weights.minutes + weights.profile;
  if (total <= 0) return null;
  const available = (
    Object.keys(components) as Array<keyof ScoutingValueWeights>
  ).reduce((sum, key) => sum + weights[key], 0);
  const coverage = available / total;
  if (coverage < valueModel.min_weight_coverage) return null;
  const value =
    (Object.entries(components) as Array<[keyof ScoutingValueWeights, number]>).reduce(
      (sum, [key, component]) => sum + weights[key] * component,
      0,
    ) / available;
  return roundHalfEven(100 * value, 1);
}

export function readerValueIndex(
  row: ScoutingPoolRow,
  weights: ScoutingValueWeights,
  document: ScoutingSearchDocument,
): number | null {
  return readerValueIndexFor(row, weights, document.value_model);
}

export function rowValueIndex(
  row: ScoutingPoolRow,
  session: ScoutingSession,
): number | null {
  return isDefaultValueWeights(session.valueWeights, session.document)
    ? row.value_index
    : readerValueIndex(row, session.valueWeights, session.document);
}

export function rowPriority(
  row: ScoutingPoolRow,
  session: ScoutingSession,
): number | null {
  return priorityFor(
    rowValueIndex(row, session),
    row.age,
    row.european_status,
    session.priority,
    session.lenses,
  );
}

export function buildPoolRows(
  document: ScoutingSearchDocument,
): ScoutingPoolRow[] {
  const leagueById = new Map(document.leagues.map((league) => [league.slug, league]));
  const profileIds =
    document.profile_order ?? Object.keys(document.profile_labels);
  return document.players.map((row: ScoutingSearchRow) => {
    const archetypes: Record<string, number | null> = {};
    const profileRaw: Record<string, number | null> = {};
    const profileCoverage: Record<string, number | null> = {};
    for (const [index, adjusted, raw, coverage] of row.arp ?? []) {
      const id = profileIds[index];
      if (!id) continue;
      archetypes[id] = adjusted;
      profileRaw[id] = raw;
      profileCoverage[id] = coverage;
    }
    const league = leagueById.get(row.l);
    return {
      player_id: row.i,
      name: row.n,
      club: row.c,
      stats_club: row.sc ?? row.c,
      league_id: league?.id ?? row.l,
      league_slug: row.l,
      league_name: league?.name ?? row.l,
      nationality: row.na ?? null,
      role_family: row.rf ?? null,
      role_label: row.rf ? document.role_labels[row.rf] ?? "Role unknown" : "Role unknown",
      age: row.a ?? null,
      minutes: row.m,
      rating: row.rt ?? null,
      rating_percentile: row.p ?? null,
      adjusted_percentile: row.ap ?? null,
      value_index: row.vi ?? null,
      value_index_coverage: row.vc ?? null,
      current_club_status: row.cs ?? null,
      european_status: row.es ?? "unknown",
      european_minutes: row.em ?? null,
      european_competitions: (row.eu ?? []).map(
        (code) => EUROPE_NAMES[code] ?? code,
      ),
      goals: row.gl ?? null,
      assists: row.ast ?? null,
      goals_p90: row.g90 ?? null,
      assists_p90: null,
      goals_assists_p90: row.ga ?? null,
      shots_p90: row.sh90 ?? null,
      conversion_pct: row.cv ?? null,
      team_rank: row.tr ?? null,
      team_points: row.tpts ?? null,
      team_count: row.tc ?? null,
      team_points_percentile: row.tpc ?? null,
      team_underperforming: row.tu ?? null,
      team_lift: row.tl ?? null,
      top_profile: row.pr ?? null,
      top_profile_score: row.psc ?? null,
      archetypes,
      profile_raw: profileRaw,
      profile_coverage: profileCoverage,
      flags: (row.f ?? []).map((code) => FLAG_NAMES[code] ?? code),
    };
  });
}

export function matchesEligibility(
  row: ScoutingPoolRow,
  session: ScoutingSession,
): boolean {
  const { lenses, filters, priority } = session;
  const needle = filters.query.trim().toLowerCase();
  if (needle) {
    const haystack = `${row.name} ${row.club} ${row.league_name}`.toLowerCase();
    if (!haystack.includes(needle)) return false;
  }
  if (lenses.league !== "all" && row.league_slug !== lenses.league) return false;
  if (lenses.role !== "all" && (row.role_family ?? "unknown") !== lenses.role) {
    return false;
  }
  if (
    lenses.archetype !== "all" &&
    row.archetypes[lenses.archetype] == null
  ) {
    return false;
  }
  if (filters.nationality !== "all" && row.nationality !== filters.nationality) {
    return false;
  }
  if (row.minutes < filters.minMinutes) return false;
  if (filters.maxAge !== null && (row.age ?? 99) > filters.maxAge) return false;
  if (lenses.u23Only && (row.age === null || row.age > priority.u23_max_age)) {
    return false;
  }
  if (lenses.excludeEurope && row.european_status === "qualified") return false;
  if (filters.europeStatus !== "any" && row.european_status !== filters.europeStatus) {
    return false;
  }
  if (filters.roleKnownOnly && row.role_family === null) return false;
  if (
    filters.minValueCoverage !== null &&
    (row.value_index_coverage ?? 0) < filters.minValueCoverage
  ) {
    return false;
  }
  if (lenses.underperformingOnly) {
    if (
      row.team_points_percentile === null ||
      row.team_points_percentile > session.teamThreshold
    ) {
      return false;
    }
  }
  return true;
}

function compareValues(
  left: number | null,
  right: number | null,
  leftMinutes: number,
  rightMinutes: number,
): number {
  if (left === null && right === null) return rightMinutes - leftMinutes;
  if (left === null) return 1;
  if (right === null) return -1;
  if (right !== left) return right - left;
  return rightMinutes - leftMinutes;
}

function mixRows(rows: ScoutingPoolRow[]): ScoutingPoolRow[] {
  const groups = new Map<string, ScoutingPoolRow[]>();
  for (const row of rows) {
    const list = groups.get(row.league_slug) ?? [];
    list.push(row);
    groups.set(row.league_slug, list);
  }
  const ordered = Array.from(groups.values()).map((list) =>
    list.sort(
      (left, right) =>
        compareValues(
          left.rating_percentile,
          right.rating_percentile,
          left.minutes,
          right.minutes,
        ),
    ),
  );
  const mixed: ScoutingPoolRow[] = [];
  let index = 0;
  while (ordered.some((list) => list.length > index)) {
    for (const list of ordered) {
      if (list.length > index) mixed.push(list[index]);
    }
    index += 1;
  }
  return mixed;
}

export function sortRows(
  rows: ScoutingPoolRow[],
  sort: ScoutingSortKey,
  session: ScoutingSession,
): ScoutingPoolRow[] {
  if (sort === "mix") return mixRows(rows);
  if (sort === "league") {
    return [...rows].sort((left, right) => {
      const league = left.league_name.localeCompare(right.league_name);
      if (league !== 0) return league;
      return compareValues(
        left.rating_percentile,
        right.rating_percentile,
        left.minutes,
        right.minutes,
      );
    });
  }
  return [...rows].sort((left, right) => {
    if (sort === "priority") {
      return compareValues(
        rowPriority(left, session),
        rowPriority(right, session),
        left.minutes,
        right.minutes,
      );
    }
    if (sort === "percentile") {
      return compareValues(
        left.rating_percentile,
        right.rating_percentile,
        left.minutes,
        right.minutes,
      );
    }
    if (sort === "adjusted") {
      return compareValues(
        left.adjusted_percentile,
        right.adjusted_percentile,
        left.minutes,
        right.minutes,
      );
    }
    if (sort === "value_index") {
      return compareValues(
        rowValueIndex(left, session),
        rowValueIndex(right, session),
        left.minutes,
        right.minutes,
      );
    }
    if (sort === "rating") {
      return compareValues(left.rating, right.rating, left.minutes, right.minutes);
    }
    if (sort === "minutes") {
      return right.minutes - left.minutes;
    }
    if (sort === "goals_assists") {
      return compareValues(
        left.goals_assists_p90,
        right.goals_assists_p90,
        left.minutes,
        right.minutes,
      );
    }
    if (sort === "team_lift") {
      return compareValues(
        left.team_lift,
        right.team_lift,
        left.minutes,
        right.minutes,
      );
    }
    if (sort === "archetype") {
      return compareValues(
        session.lenses.archetype === "all"
          ? null
          : left.archetypes[session.lenses.archetype] ?? null,
        session.lenses.archetype === "all"
          ? null
          : right.archetypes[session.lenses.archetype] ?? null,
        left.minutes,
        right.minutes,
      );
    }
    return 0;
  });
}

function leaderFor(
  row: ScoutingPoolRow,
  profileId: string,
  session: ScoutingSession,
): ScoutingLeader {
  const multiplier = ageFactor(row.age, session.priority, session.lenses);
  const europe = europeFactor(
    row.european_status,
    session.priority,
    session.lenses,
  );
  return {
    player_id: row.player_id,
    name: row.name,
    club: row.club,
    league_id: row.league_id,
    league_slug: row.league_slug,
    league_name: row.league_name,
    stats_club: row.stats_club,
    current_club_status: row.current_club_status ?? "unknown",
    age: row.age,
    minutes: row.minutes,
    rating: row.rating,
    rating_percentile: row.rating_percentile,
    adjusted_percentile: row.adjusted_percentile,
    raw_score: row.profile_raw[profileId] ?? null,
    adjusted_score: row.archetypes[profileId] ?? null,
    coverage: row.profile_coverage[profileId] ?? null,
    value_index: row.value_index,
    value_index_coverage: row.value_index_coverage,
    team_context_status:
      row.team_points_percentile === null ? "unknown" : "available",
    team_rank: row.team_rank,
    team_points: row.team_points,
    team_played: null,
    team_ppg: null,
    team_count: row.team_count,
    team_points_percentile: row.team_points_percentile,
    team_underperforming: row.team_underperforming,
    team_lift: row.team_lift,
    scouting_priority: rowPriority(row, session),
    age_multiplier: multiplier,
    europe_multiplier: europe,
    european_league_phase_minutes: row.european_minutes,
    european_league_phase_competitions: row.european_competitions,
    european_status: row.european_status,
  };
}

export function readerArchetypes(
  published: ScoutingArchetypeDefinition[],
  rows: ScoutingPoolRow[],
  session: ScoutingSession,
): ScoutingArchetypeDefinition[] {
  const minCoverage = session.document.archetype_min_coverage;
  return published.map((definition) => {
    const limit = Math.max(definition.leaders.length, 1);
    const candidates = rows.filter((row) => {
      const coverage = row.profile_coverage[definition.id];
      return (
        row.archetypes[definition.id] != null &&
        coverage != null &&
        coverage >= minCoverage &&
        matchesEligibility(row, session)
      );
    });
    candidates.sort((left, right) => {
      if (session.lenses.priorityActive) {
        return compareValues(
          rowPriority(left, session),
          rowPriority(right, session),
          left.minutes,
          right.minutes,
        );
      }
      const leftRank = profileRank(
        left.archetypes[definition.id] ?? null,
        left.age,
        left.european_status,
        session.priority,
        session.lenses,
      );
      const rightRank = profileRank(
        right.archetypes[definition.id] ?? null,
        right.age,
        right.european_status,
        session.priority,
        session.lenses,
      );
      if (leftRank !== rightRank) {
        return (rightRank ?? -1) - (leftRank ?? -1);
      }
      return compareValues(
        left.archetypes[definition.id] ?? null,
        right.archetypes[definition.id] ?? null,
        left.minutes,
        right.minutes,
      );
    });
    return {
      ...definition,
      leaders: candidates
        .slice(0, limit)
        .map((row) => leaderFor(row, definition.id, session)),
    };
  });
}

function attackerCandidates(
  rows: ScoutingPoolRow[],
  session: ScoutingSession,
): Array<{ row: ScoutingPoolRow; bias: number }> {
  return rows
    .filter((row) => {
      if (!row.role_family || !ATTACK_FAMILIES.has(row.role_family)) return false;
      if (
        row.archetypes.assist_creator == null ||
        row.archetypes.goal_scorer == null
      ) {
        return false;
      }
      return matchesEligibility(row, session);
    })
    .map((row) => ({
      row,
      bias: (row.archetypes.assist_creator ?? 0) - (row.archetypes.goal_scorer ?? 0),
    }));
}

function sortAttackers(
  candidates: Array<{ row: ScoutingPoolRow; bias: number }>,
  profileId: "assist_creator" | "goal_scorer",
  session: ScoutingSession,
): ScoutingPoolRow[] {
  return [...candidates]
    .sort((left, right) => {
      if (session.lenses.priorityActive) {
        return compareValues(
          rowPriority(left.row, session),
          rowPriority(right.row, session),
          left.row.minutes,
          right.row.minutes,
        );
      }
      const leftRank = profileRank(
        left.row.archetypes[profileId] ?? null,
        left.row.age,
        left.row.european_status,
        session.priority,
        session.lenses,
      );
      const rightRank = profileRank(
        right.row.archetypes[profileId] ?? null,
        right.row.age,
        right.row.european_status,
        session.priority,
        session.lenses,
      );
      if (leftRank !== rightRank) {
        return (rightRank ?? -1) - (leftRank ?? -1);
      }
      const bias =
        profileId === "assist_creator"
          ? right.bias - left.bias
          : left.bias - right.bias;
      if (bias !== 0) return bias;
      return compareValues(
        rowPriority(left.row, session),
        rowPriority(right.row, session),
        left.row.minutes,
        right.row.minutes,
      );
    })
    .map((item) => item.row);
}

export function readerAttackers(
  published: ScoutingAttackers,
  rows: ScoutingPoolRow[],
  session: ScoutingSession,
): ScoutingAttackers {
  const candidates = attackerCandidates(rows, session);
  const assist = sortAttackers(
    candidates.filter((item) => item.bias > 0),
    "assist_creator",
    session,
  );
  const goal = sortAttackers(
    candidates.filter((item) => item.bias < 0),
    "goal_scorer",
    session,
  );
  const withBias = (row: ScoutingPoolRow, profileId: string): ScoutingLeader => {
    const leader = leaderFor(row, profileId, session);
    return {
      ...leader,
      bias: roundHalfEven(
        (row.archetypes.assist_creator ?? 0) - (row.archetypes.goal_scorer ?? 0),
        1,
      ),
      assist_score: row.archetypes.assist_creator ?? null,
      goal_score: row.archetypes.goal_scorer ?? null,
    };
  };
  return {
    ...published,
    assist_bias: {
      ...published.assist_bias,
      leaders: assist
        .slice(0, Math.max(published.assist_bias.leaders.length, 1))
        .map((row) => withBias(row, "assist_creator")),
    },
    goal_bias: {
      ...published.goal_bias,
      leaders: goal
        .slice(0, Math.max(published.goal_bias.leaders.length, 1))
        .map((row) => withBias(row, "goal_scorer")),
    },
  };
}

export function readerGoalScorers(
  published: ScoutingGoalScorer[],
  rows: ScoutingPoolRow[],
  session: ScoutingSession,
): ScoutingGoalScorer[] {
  const limit = Math.max(published.length, 1);
  return rows
    .filter((row) => {
      if (!row.role_family || !ATTACK_FAMILIES.has(row.role_family)) return false;
      if (row.goals_p90 == null) return false;
      return matchesEligibility(row, session);
    })
    .sort((left, right) => {
      if (left.goals_p90 !== right.goals_p90) {
        return (right.goals_p90 ?? -1) - (left.goals_p90 ?? -1);
      }
      if (left.goals_assists_p90 !== right.goals_assists_p90) {
        return (right.goals_assists_p90 ?? -1) - (left.goals_assists_p90 ?? -1);
      }
      return right.minutes - left.minutes;
    })
    .slice(0, limit)
    .map((row) => ({
      player_id: row.player_id,
      name: row.name,
      club: row.club,
      stats_club: row.stats_club,
      league_id: row.league_id,
      league_slug: row.league_slug,
      league_name: row.league_name,
      age: row.age,
      minutes: row.minutes,
      goals: row.goals,
      assists: row.assists,
      goals_p90: row.goals_p90,
      assists_p90: row.assists_p90,
      goals_assists_p90: row.goals_assists_p90,
      shots_p90: row.shots_p90,
      conversion_pct: row.conversion_pct,
      scouting_priority: rowPriority(row, session),
      value_index: row.value_index,
      european_status: row.european_status,
      european_league_phase_minutes: row.european_minutes,
      current_club_status: row.current_club_status ?? "unknown",
    }));
}

export function readerTeamLeaders(
  published: ScoutingLeader[],
  rows: ScoutingPoolRow[],
  session: ScoutingSession,
): ScoutingLeader[] {
  const limit = Math.max(published.length, 1);
  return rows
    .filter((row) => {
      if (row.team_points_percentile === null) return false;
      if (row.team_points_percentile > session.teamThreshold) return false;
      if (row.team_lift === null || row.team_lift <= session.minLift) return false;
      return matchesEligibility(row, session);
    })
    .sort((left, right) => {
      if (session.lenses.priorityActive) {
        return compareValues(
          rowPriority(left, session),
          rowPriority(right, session),
          left.minutes,
          right.minutes,
        );
      }
      if (left.team_lift !== right.team_lift) {
        return (right.team_lift ?? -1) - (left.team_lift ?? -1);
      }
      return compareValues(
        rowPriority(left, session),
        rowPriority(right, session),
        left.minutes,
        right.minutes,
      );
    })
    .slice(0, limit)
    .map((row) => {
      const profileId =
        row.top_profile ??
        Object.entries(row.archetypes)
          .filter(([, score]) => score !== null)
          .sort((left, right) => (right[1] ?? -1) - (left[1] ?? -1))[0]?.[0] ??
        "";
      return leaderFor(row, profileId, session);
    });
}
