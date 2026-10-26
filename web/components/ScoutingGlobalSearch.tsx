"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ScoutingLensSelector } from "@/components/ScoutingLensSelector";
import { TableFrame } from "@/components/TableFrame";
import type {
  ScoutingArchetypeDefinition,
  ScoutingPriorityConfig,
  ScoutingSearchDocument,
  ScoutingSearchRow,
} from "@/lib/data";
import {
  defaultValueWeights,
  isDefaultValueWeights,
  readerValueIndexFor,
  type ScoutingValueWeights,
} from "@/lib/scouting-filters";
import {
  formatDecimal,
  formatInteger,
  formatPercentValue,
  roundHalfEven,
} from "@/lib/format";

type SortKey =
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

type Row = {
  player_id: number;
  name: string;
  club: string;
  stats_club: string;
  team_rank: number | null;
  team_points: number | null;
  team_count: number | null;
  team_points_percentile: number | null;
  team_underperforming: boolean | null;
  team_lift: number | null;
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
  display_value_index: number | null;
  value_index_coverage: number | null;
  european_status: string;
  european_minutes: number | null;
  european_competitions: string[];
  priority: number | null;
  goals_assists_p90: number | null;
  dribbles_success_p90: number | null;
  passes_completed_p90: number | null;
  pass_completion_pct: number | null;
  key_passes_p90: number | null;
  tackles_p90: number | null;
  interceptions_p90: number | null;
  duel_win_pct: number | null;
  flags: string[];
  archetypes: Record<string, number | null>;
  profile: { id: string; label: string; score: number } | null;
};

const FLAG_CODES: Record<string, string> = {
  l: "low_minutes",
  r: "role_unknown",
  n: "no_rating",
};

const EUROPE_LABELS: Record<string, string> = {
  ucl: "UCL",
  uel: "UEL",
  uecl: "UECL",
};

const SORT_LABELS: Record<SortKey, string> = {
  priority: "Scouting priority",
  mix: "League mix",
  league: "League, then percentile",
  percentile: "Within-league percentile",
  adjusted: "Adjusted percentile",
  value_index: "Value index",
  rating: "Provider rating",
  minutes: "Minutes",
  goals_assists: "Goals + assists /90",
  archetype: "Profile score",
  team_lift: "Team lift",
};

const EUROPE_STATUS_OPTIONS = [
  ["any", "Any European status"],
  ["qualified", "League-phase qualified"],
  ["below_threshold", "Below the minutes threshold"],
  ["none", "No European league phase"],
  ["unknown", "Unknown"],
] as const;

function value(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? "—" : formatDecimal(value, digits);
}

function percentile(value: number | null): string {
  return value === null || value === undefined ? "—" : formatPercentValue(value, 1);
}

function percentage(value: number | null): string {
  return value === null || value === undefined ? "—" : formatPercentValue(value, 1);
}

function qualifiesForEurope(player: Row, threshold: number): boolean {
  if (player.european_status === "unknown") return false;
  return (player.european_minutes ?? 0) >= threshold;
}

function effectiveEuropeStatus(player: Row, threshold: number): string {
  if (player.european_status === "unknown") return "unknown";
  const minutes = player.european_minutes ?? 0;
  if (minutes >= threshold) return "qualified";
  return minutes > 0 ? "below_threshold" : "none";
}

function priorityFor(
  player: Row,
  weights: ScoutingPriorityConfig,
  u23Boost: boolean,
  europeDiscount: boolean,
  valueIndex: number | null,
): number | null {
  if (valueIndex === null) return null;
  const ageMultiplier =
    u23Boost && player.age !== null && player.age <= weights.u23_max_age
      ? weights.u23_multiplier
      : 1;
  const europeMultiplier =
    europeDiscount && qualifiesForEurope(player, weights.europe_minutes_threshold)
      ? weights.europe_multiplier
      : 1;
  return roundHalfEven(valueIndex * ageMultiplier * europeMultiplier, 1);
}

function sortValue(player: Row, key: SortKey, archetype: string): number | null {
  if (key === "priority") return player.priority;
  if (key === "percentile") return player.rating_percentile;
  if (key === "adjusted") return player.adjusted_percentile;
  if (key === "value_index") return player.display_value_index;
  if (key === "rating") return player.rating;
  if (key === "minutes") return player.minutes;
  if (key === "goals_assists") return player.goals_assists_p90;
  if (key === "archetype") return player.archetypes[archetype] ?? null;
  if (key === "team_lift") return player.team_lift;
  return null;
}

function europeLabel(player: Row): string {
  if (player.european_status === "unknown") return "Unknown";
  if (player.european_status === "none") return "—";
  const competitions = player.european_competitions
    .map((code) => EUROPE_LABELS[code] ?? code)
    .join("/");
  const minutes = player.european_minutes ?? 0;
  return competitions ? `${competitions} · ${minutes}m` : `${minutes}m`;
}

export function ScoutingGlobalSearch({
  document,
  archetypes,
  initialPlayers,
  shardPaths,
}: {
  document: ScoutingSearchDocument;
  archetypes: ScoutingArchetypeDefinition[];
  initialPlayers?: ScoutingSearchRow[];
  shardPaths?: string[];
}) {
  const publishedWeights: ScoutingPriorityConfig = document.priority ?? {
    u23_max_age: 23,
    u23_multiplier: 1.3,
    europe_minutes_threshold: 90,
    europe_multiplier: 0.6,
  };
  const publishedValueWeights = defaultValueWeights(document);

  const [query, setQuery] = useState("");
  const [league, setLeague] = useState("all");
  const [role, setRole] = useState("all");
  const [nationality, setNationality] = useState("all");
  const [archetype, setArchetype] = useState("all");
  const [minMinutes, setMinMinutes] = useState(String(document.min_minutes));
  const [maxAge, setMaxAge] = useState("all");
  const [europeStatus, setEuropeStatus] = useState("any");
  const [roleKnownOnly, setRoleKnownOnly] = useState(false);
  const [minValueCoverage, setMinValueCoverage] = useState("any");
  const [u23Boost, setU23Boost] = useState(true);
  const [u23Only, setU23Only] = useState(false);
  const [europeDiscount, setEuropeDiscount] = useState(true);
  const [excludeEurope, setExcludeEurope] = useState(false);
  const [underperformingOnly, setUnderperformingOnly] = useState(false);
  const [sort, setSort] = useState<SortKey>("mix");
  const [limit, setLimit] = useState(100);
  const [searchRows, setSearchRows] = useState<ScoutingSearchRow[]>(
    initialPlayers ?? document.players,
  );
  const [shardState, setShardState] = useState<
    "ready" | "loading" | "partial" | "error"
  >(
    shardPaths?.length && (initialPlayers?.length ?? 0) < document.count
      ? "partial"
      : "ready",
  );

  const [u23MaxAge, setU23MaxAge] = useState(publishedWeights.u23_max_age);
  const [u23Multiplier, setU23Multiplier] = useState(publishedWeights.u23_multiplier);
  const [europeThreshold, setEuropeThreshold] = useState(
    publishedWeights.europe_minutes_threshold,
  );
  const [europeMultiplier, setEuropeMultiplier] = useState(
    publishedWeights.europe_multiplier,
  );
  const [valueWeights, setValueWeights] =
    useState<ScoutingValueWeights>(publishedValueWeights);
  const [teamThreshold, setTeamThreshold] = useState(
    document.team_context.underperforming_ppg_percentile_max,
  );
  const [teamMinLift, setTeamMinLift] = useState(document.team_context.min_lift);

  const weights = useMemo<ScoutingPriorityConfig>(
    () => ({
      u23_max_age: u23MaxAge,
      u23_multiplier: u23Multiplier,
      europe_minutes_threshold: europeThreshold,
      europe_multiplier: europeMultiplier,
    }),
    [u23MaxAge, u23Multiplier, europeThreshold, europeMultiplier],
  );
  const valueWeightTotal =
    valueWeights.performance +
    valueWeights.age +
    valueWeights.minutes +
    valueWeights.profile;
  const valueWeightsValid = valueWeightTotal > 0;
  const advancedDefault =
    u23MaxAge === publishedWeights.u23_max_age &&
    u23Multiplier === publishedWeights.u23_multiplier &&
    europeThreshold === publishedWeights.europe_minutes_threshold &&
    europeMultiplier === publishedWeights.europe_multiplier &&
    isDefaultValueWeights(valueWeights, document) &&
    teamThreshold === document.team_context.underperforming_ppg_percentile_max &&
    teamMinLift === document.team_context.min_lift;
  const basicDefault =
    query.trim() === "" &&
    league === "all" &&
    role === "all" &&
    nationality === "all" &&
    archetype === "all" &&
    minMinutes === String(document.min_minutes) &&
    maxAge === "all" &&
    europeStatus === "any" &&
    !roleKnownOnly &&
    minValueCoverage === "any" &&
    u23Boost &&
    !u23Only &&
    europeDiscount &&
    !excludeEurope &&
    !underperformingOnly &&
    sort === "mix";
  const isDefault = advancedDefault && basicDefault;

  useEffect(() => {
    if (!shardPaths?.length) return;
    if (searchRows.length >= document.count) return;
    let cancelled = false;
    setShardState("loading");
    Promise.all(
      shardPaths.map(async (path) => {
        const response = await fetch(path, { cache: "force-cache" });
        if (!response.ok) throw new Error(`shard ${response.status}`);
        const payload = (await response.json()) as { players?: ScoutingSearchRow[] };
        return payload.players ?? [];
      }),
    )
      .then((parts) => {
        if (cancelled) return;
        setSearchRows(parts.flat());
        setShardState("ready");
      })
      .catch(() => {
        if (!cancelled) setShardState("error");
      });
    return () => {
      cancelled = true;
    };
    // Fetch once after the first paint; filter changes operate on the loaded set.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shardPaths, document.count]);

  const leagueBySlug = useMemo(
    () => new Map(document.leagues.map((league) => [league.slug, league])),
    [document.leagues],
  );
  const profileIds = useMemo(
    () => document.profile_order ?? Object.keys(document.profile_labels),
    [document.profile_order, document.profile_labels],
  );
  const players = useMemo<Row[]>(
    () =>
      searchRows.map((row) => ({
        player_id: row.i,
        name: row.n,
        club: row.c,
        stats_club: row.sc ?? row.c,
        team_rank: row.tr ?? null,
        team_points: row.tpts ?? null,
        team_count: row.tc ?? null,
        team_points_percentile: row.tpc ?? null,
        team_underperforming: row.tu ?? null,
        team_lift: row.tl ?? null,
        league_slug: row.l,
        league_name: leagueBySlug.get(row.l)?.name ?? row.l,
        nationality: row.na ?? null,
        role_family: row.rf ?? null,
        role_label: row.rf
          ? document.role_labels[row.rf] ?? "Role unknown"
          : "Role unknown",
        age: row.a ?? null,
        minutes: row.m,
        rating: row.rt ?? null,
        rating_percentile: row.p ?? null,
        adjusted_percentile: row.ap ?? null,
        value_index: row.vi ?? null,
        display_value_index: row.vi ?? null,
        value_index_coverage: row.vc ?? null,
        european_status: row.es ?? "unknown",
        european_minutes: row.em ?? null,
        european_competitions: row.eu ?? [],
        priority: null,
        goals_assists_p90: row.ga ?? null,
        dribbles_success_p90: row.dr ?? null,
        passes_completed_p90: row.ps ?? null,
        pass_completion_pct: row.pa ?? null,
        key_passes_p90: row.kp ?? null,
        tackles_p90: row.tk ?? null,
        interceptions_p90: row.it ?? null,
        duel_win_pct: row.dw ?? null,
        flags: (row.f ?? []).map((code) => FLAG_CODES[code] ?? code),
        archetypes: Object.fromEntries(
          (row.arp ?? [])
            .filter(([index]) => profileIds[index] !== undefined)
            .map(([index, adjusted]) => [profileIds[index], adjusted]),
        ),
        profile: row.pr
          ? {
              id: row.pr,
              label: document.profile_labels[row.pr] ?? row.pr,
              score: row.psc ?? 0,
            }
          : null,
      })),
    [searchRows, document.role_labels, profileIds, leagueBySlug],
  );

  useEffect(() => {
    setLimit(100);
  }, [
    query,
    league,
    role,
    nationality,
    archetype,
    minMinutes,
    maxAge,
    europeStatus,
    roleKnownOnly,
    minValueCoverage,
    u23Boost,
    u23Only,
    europeDiscount,
    excludeEurope,
    underperformingOnly,
    sort,
    u23MaxAge,
    u23Multiplier,
    europeThreshold,
    europeMultiplier,
    valueWeights,
    teamThreshold,
    teamMinLift,
  ]);

  useEffect(() => {
    const hash = window.location.hash.replace("#", "");
    if (archetypes.some((item) => item.id === hash)) {
      setArchetype(hash);
      setSort("archetype");
    }
  }, [archetypes]);

  const leagues = useMemo(
    () =>
      document.leagues
        .filter((item) => item.players > 0)
        .sort((left, right) => left.name.localeCompare(right.name)),
    [document.leagues],
  );

  const roles = useMemo(() => {
    const seen = new Map<string, string>();
    for (const player of players) {
      const key = player.role_family ?? "unknown";
      if (!seen.has(key)) seen.set(key, player.role_label);
    }
    return Array.from(seen.entries()).sort((left, right) => left[1].localeCompare(right[1]));
  }, [players]);

  const nationalities = useMemo(() => {
    const seen = new Set<string>();
    for (const player of players) {
      if (player.nationality) seen.add(player.nationality);
    }
    return Array.from(seen).sort((left, right) => left.localeCompare(right));
  }, [players]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const minimum = Number(minMinutes);
    const ageLimit = maxAge === "all" ? null : Number(maxAge);
    const coverageLimit =
      minValueCoverage === "any" ? null : Number(minValueCoverage);
    const matched = players
      .filter((player) => {
        if (needle) {
          const haystack = `${player.name} ${player.club} ${player.league_name}`.toLowerCase();
          if (!haystack.includes(needle)) return false;
        }
        if (league !== "all" && player.league_slug !== league) return false;
        if (role !== "all" && (player.role_family ?? "unknown") !== role) return false;
        if (nationality !== "all" && player.nationality !== nationality) return false;
        if (archetype !== "all" && player.archetypes[archetype] == null) return false;
        if (player.minutes < minimum) return false;
        if (ageLimit !== null && (player.age ?? 99) > ageLimit) return false;
        if (
          europeStatus !== "any" &&
          effectiveEuropeStatus(player, weights.europe_minutes_threshold) !==
            europeStatus
        ) {
          return false;
        }
        if (roleKnownOnly && player.role_family === null) return false;
        if (
          coverageLimit !== null &&
          (player.value_index_coverage ?? 0) < coverageLimit
        ) {
          return false;
        }
        if (u23Only && (player.age === null || player.age > weights.u23_max_age)) {
          return false;
        }
        if (
          excludeEurope &&
          qualifiesForEurope(player, weights.europe_minutes_threshold)
        ) {
          return false;
        }
        if (underperformingOnly) {
          if (
            player.team_points_percentile === null ||
            player.team_points_percentile > teamThreshold ||
            (player.team_lift ?? 0) <= teamMinLift
          ) {
            return false;
          }
        }
        return true;
      })
      .map((player) => {
        const readerValue = valueWeightsValid
          ? isDefaultValueWeights(valueWeights, document)
            ? player.value_index
            : readerValueIndexFor(player, valueWeights, document.value_model)
          : null;
        return {
          ...player,
          display_value_index: readerValue,
          priority: priorityFor(
            player,
            weights,
            u23Boost,
            europeDiscount,
            readerValue,
          ),
        };
      });
    if (sort === "mix") {
      const groups = new Map<string, Row[]>();
      for (const player of matched) {
        const list = groups.get(player.league_slug) ?? [];
        list.push(player);
        groups.set(player.league_slug, list);
      }
      const ordered = Array.from(groups.values()).map((list) =>
        list.sort((left, right) => {
          const leftPct = left.rating_percentile ?? -1;
          const rightPct = right.rating_percentile ?? -1;
          if (rightPct !== leftPct) return rightPct - leftPct;
          return right.minutes - left.minutes;
        }),
      );
      const mixed: Row[] = [];
      let index = 0;
      while (ordered.some((list) => list.length > index)) {
        for (const list of ordered) {
          if (list.length > index) mixed.push(list[index]);
        }
        index += 1;
      }
      return mixed;
    }
    return matched.sort((left, right) => {
      if (sort === "league") {
        const leagueDelta = left.league_name.localeCompare(right.league_name);
        if (leagueDelta !== 0) return leagueDelta;
        const leftPct = left.rating_percentile ?? -1;
        const rightPct = right.rating_percentile ?? -1;
        if (rightPct !== leftPct) return rightPct - leftPct;
        return right.minutes - left.minutes;
      }
      const leftValue = sortValue(left, sort, archetype);
      const rightValue = sortValue(right, sort, archetype);
      if (leftValue === null && rightValue === null) return 0;
      if (leftValue === null) return 1;
      if (rightValue === null) return -1;
      if (rightValue !== leftValue) return rightValue - leftValue;
      return right.minutes - left.minutes;
    });
  }, [
    players,
    query,
    league,
    role,
    nationality,
    archetype,
    minMinutes,
    maxAge,
    europeStatus,
    roleKnownOnly,
    minValueCoverage,
    u23Boost,
    u23Only,
    europeDiscount,
    excludeEurope,
    underperformingOnly,
    sort,
    weights,
    valueWeights,
    valueWeightsValid,
    teamThreshold,
    document,
  ]);

  const visible = filtered.slice(0, limit);

  const resetAll = () => {
    setQuery("");
    setLeague("all");
    setRole("all");
    setNationality("all");
    setArchetype("all");
    setMinMinutes(String(document.min_minutes));
    setMaxAge("all");
    setEuropeStatus("any");
    setRoleKnownOnly(false);
    setMinValueCoverage("any");
    setU23Boost(true);
    setU23Only(false);
    setEuropeDiscount(true);
    setExcludeEurope(false);
    setUnderperformingOnly(false);
    setSort("mix");
    setU23MaxAge(publishedWeights.u23_max_age);
    setU23Multiplier(publishedWeights.u23_multiplier);
    setEuropeThreshold(publishedWeights.europe_minutes_threshold);
    setEuropeMultiplier(publishedWeights.europe_multiplier);
    setValueWeights(publishedValueWeights);
    setTeamThreshold(document.team_context.underperforming_ppg_percentile_max);
    setTeamMinLift(document.team_context.min_lift);
  };

  return (
    <div>
      <div className="board-controls">
        <ScoutingLensSelector
          priorityActive={sort === "priority"}
          onPriorityChange={(active) => setSort(active ? "priority" : "adjusted")}
          u23Boost={u23Boost}
          setU23Boost={setU23Boost}
          u23Only={u23Only}
          setU23Only={setU23Only}
          europeDiscount={europeDiscount}
          setEuropeDiscount={setEuropeDiscount}
          excludeEurope={excludeEurope}
          setExcludeEurope={setExcludeEurope}
          underperformingOnly={underperformingOnly}
          setUnderperformingOnly={setUnderperformingOnly}
          archetype={archetype}
          setArchetype={(value) => {
            setArchetype(value);
            if (value !== "all") setSort("archetype");
            else if (sort === "archetype") setSort("priority");
          }}
          role={role}
          setRole={setRole}
          league={league}
          setLeague={setLeague}
          leagues={leagues}
          roles={roles}
          archetypes={archetypes}
          priority={weights}
          isDefault={isDefault}
        />
        <label>
          Sort
          <select value={sort} onChange={(event) => setSort(event.target.value as SortKey)}>
            {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
              <option key={key} value={key}>
                {SORT_LABELS[key]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <section className="card advanced-filters" data-contract="scouting.advanced-filters">
        <div className="card-head">
          <div>
            <p className="eyebrow">Reader controls</p>
            <h3>Advanced filters</h3>
          </div>
          <div className="advanced-actions">
            <span className={`badge ${isDefault ? "badge-neutral" : "badge-warn"}`}>
              {isDefault ? "Published defaults" : "Reader scenario"}
            </span>
            <button type="button" className="button button-ghost" onClick={resetAll}>
              Reset all filters and lenses
            </button>
          </div>
        </div>

        <div className="advanced-grid">
          <fieldset className="advanced-group">
            <legend>U23 and Europe weights</legend>
            <label>
              U23 cutoff
              <span className="advanced-value">{formatInteger(u23MaxAge)}</span>
              <input
                type="range"
                min={18}
                max={27}
                step={1}
                value={u23MaxAge}
                onChange={(event) => setU23MaxAge(Number(event.target.value))}
              />
            </label>
            <label>
              U23 multiplier
              <span className="advanced-value">{formatDecimal(u23Multiplier, 2)}</span>
              <input
                type="range"
                min={1}
                max={2}
                step={0.05}
                value={u23Multiplier}
                onChange={(event) => setU23Multiplier(Number(event.target.value))}
              />
            </label>
            <label>
              Europe minutes threshold
              <span className="advanced-value">{formatInteger(europeThreshold)}</span>
              <input
                type="range"
                min={0}
                max={450}
                step={45}
                value={europeThreshold}
                onChange={(event) => setEuropeThreshold(Number(event.target.value))}
              />
            </label>
            <label>
              Europe multiplier
              <span className="advanced-value">{formatDecimal(europeMultiplier, 2)}</span>
              <input
                type="range"
                min={0.2}
                max={1}
                step={0.05}
                value={europeMultiplier}
                onChange={(event) => setEuropeMultiplier(Number(event.target.value))}
              />
            </label>
            <p className="fine-print">
              The U23 and Europe chips in the lens bar switch these preferences on
              or off; these controls set their values.
            </p>
          </fieldset>

          <fieldset className="advanced-group">
            <legend>Value-index weights</legend>
            {(
              [
                ["performance", "Performance"],
                ["age", "Age curve"],
                ["minutes", "Minutes reliability"],
                ["profile", "Profile fit"],
              ] as const
            ).map(([key, label]) => (
              <label key={key}>
                {label}
                <span className="advanced-value">
                  {formatDecimal(valueWeights[key], 2)}
                  {valueWeightTotal > 0
                    ? ` (${formatPercentValue((valueWeights[key] / valueWeightTotal) * 100, 0)})`
                    : ""}
                </span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={valueWeights[key]}
                  onChange={(event) =>
                    setValueWeights((current) => ({
                      ...current,
                      [key]: Number(event.target.value),
                    }))
                  }
                />
              </label>
            ))}
            {!valueWeightsValid ? (
              <p className="fine-print" role="status">
                At least one value-index weight must be positive; the published
                value index is shown.
              </p>
            ) : (
              <p className="fine-print">
                Weights are renormalised over the components present; the
                published index is unchanged.
              </p>
            )}
          </fieldset>

          <fieldset className="advanced-group">
            <legend>Team-context thresholds</legend>
            <label>
              Underperforming PPG percentile max
              <span className="advanced-value">{formatInteger(teamThreshold)}</span>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={teamThreshold}
                onChange={(event) => setTeamThreshold(Number(event.target.value))}
              />
            </label>
            <label>
              Minimum team lift
              <span className="advanced-value">{formatDecimal(teamMinLift, 1)}</span>
              <input
                type="range"
                min={0}
                max={50}
                step={1}
                value={teamMinLift}
                onChange={(event) => setTeamMinLift(Number(event.target.value))}
              />
            </label>
            <p className="fine-print">
              The Struggling team chip uses this threshold. Lift is a contrast,
              not a valuation.
            </p>
          </fieldset>

          <fieldset className="advanced-group">
            <legend>Eligibility filters</legend>
            <label>
              Search
              <input
                type="search"
                value={query}
                placeholder="Name, club or league"
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
            <label>
              Nationality
              <select
                value={nationality}
                onChange={(event) => setNationality(event.target.value)}
              >
                <option value="all">All nationalities</option>
                {nationalities.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Minimum minutes
              <select
                value={minMinutes}
                onChange={(event) => setMinMinutes(event.target.value)}
              >
                <option value="450">450</option>
                <option value="600">600</option>
                <option value="900">900</option>
              </select>
            </label>
            <label>
              Maximum age
              <select value={maxAge} onChange={(event) => setMaxAge(event.target.value)}>
                <option value="all">Any</option>
                <option value="21">21</option>
                <option value="24">24</option>
                <option value="27">27</option>
                <option value="30">30</option>
              </select>
            </label>
            <label>
              European status
              <select
                value={europeStatus}
                onChange={(event) => setEuropeStatus(event.target.value)}
              >
                {EUROPE_STATUS_OPTIONS.map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Minimum value-index coverage
              <select
                value={minValueCoverage}
                onChange={(event) => setMinValueCoverage(event.target.value)}
              >
                <option value="any">Any</option>
                <option value="0.5">0.50</option>
                <option value="0.7">0.70</option>
                <option value="0.85">0.85</option>
                <option value="1">1.00</option>
              </select>
            </label>
            <label className="advanced-check">
              <input
                type="checkbox"
                checked={roleKnownOnly}
                onChange={(event) => setRoleKnownOnly(event.target.checked)}
              />
              Role known only
            </label>
          </fieldset>
        </div>
        <p className="fine-print" aria-live="polite" data-contract-indicator="basis">
          {isDefault
            ? `Published defaults: U23 ≤${formatInteger(publishedWeights.u23_max_age)} ×${formatDecimal(publishedWeights.u23_multiplier, 2)}; Europe ≥${formatInteger(publishedWeights.europe_minutes_threshold)} min ×${formatDecimal(publishedWeights.europe_multiplier, 2)}.`
            : "Reader scenario: the active filters and weights change the displayed value index and priority only; the published values and audit are unchanged."}
        </p>
      </section>

      <p className="fine-print" aria-live="polite" data-contract-indicator="basis">
        {shardState === "loading" ? "Loading the full scouting pool. " : null}
        {shardState === "error"
          ? "The full pool could not be loaded; showing the initial rows only. "
          : null}
        Showing {formatInteger(visible.length)} of {formatInteger(filtered.length)} matches from{" "}
        {formatInteger(players.length)} ranked players across {formatInteger(leagues.length)}{" "}
        leagues. Priority = value index × U23 multiplier × European league-phase multiplier.
        U23 ≤{formatInteger(weights.u23_max_age)} ×
        {formatDecimal(weights.u23_multiplier, 2)}; European league phase ≥
        {formatInteger(weights.europe_minutes_threshold)} min ×
        {formatDecimal(weights.europe_multiplier, 2)}. These are Aberdeen scouting preferences,
        not measured quality. Unknown Europe status is not discounted.
      </p>
      <TableFrame label="Scouting search results">
        <table className="league-table compact">
          <caption className="fine-print">
            The full licensed scouting pool at {formatInteger(document.min_minutes)}+ minutes.
            Club is the current club from the provider transfer feed; League is where the
            2026-27 statistics were produced. Pct is relative to that league and role cohort;
            Adj Pct maps that standing into the actual Premiership distribution. The value index is not a transfer
            value and the priority is a scouting preference. A dash means the feed does not
            supply the value.
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Club</th>
              <th scope="col">Team</th>
              <th className="num" scope="col">Lift</th>
              <th scope="col">League</th>
              <th scope="col">Nationality</th>
              <th scope="col">Role</th>
              <th className="num" scope="col">Age</th>
              <th className="num" scope="col">Mins</th>
              <th className="num" scope="col">Rating</th>
              <th className="num" scope="col">Pct</th>
              <th className="num" scope="col">Adj Pct</th>
              <th className="num" scope="col">Value index</th>
              <th className="num" scope="col">Priority</th>
              <th scope="col">Europe</th>
              <th className="num" scope="col">G+A/90</th>
              <th className="num" scope="col">Dribbles/90</th>
              <th className="num" scope="col">Passes/90</th>
              <th className="num" scope="col">Pass %</th>
              <th className="num" scope="col">Key passes/90</th>
              <th className="num" scope="col">Tackles/90</th>
              <th className="num" scope="col">Interceptions/90</th>
              <th className="num" scope="col">Duels won %</th>
              <th scope="col">Profile</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((player) => (
              <tr key={`${player.player_id}-${player.league_slug}`}>
                <td>
                  <Link href={`/scouting/player/${player.player_id}/`}>
                    {player.name}
                  </Link>
                </td>
                <td>
                  {player.club}
                  {player.stats_club && player.stats_club !== player.club ? (
                    <span className="muted"> · stats at {player.stats_club}</span>
                  ) : null}
                </td>
                <td>
                  {player.team_rank === null || player.team_count === null
                    ? "—"
                    : `${player.team_rank}/${player.team_count}`}
                  {player.team_points !== null ? (
                    <span className="muted"> · {player.team_points} pts</span>
                  ) : null}
                </td>
                <td className="num">{value(player.team_lift, 1)}</td>
                <td>{player.league_name}</td>
                <td>{player.nationality ?? "—"}</td>
                <td>
                  {player.role_label}
                  {player.flags.includes("role_unknown") ? (
                    <span className="badge badge-neutral"> role unknown</span>
                  ) : null}
                </td>
                <td className="num">
                  {value(player.age, 0)}
                  {player.age !== null && player.age <= weights.u23_max_age ? (
                    <span className="badge badge-neutral"> U23</span>
                  ) : null}
                </td>
                <td className="num">
                  {formatInteger(player.minutes)}
                  {player.flags.includes("low_minutes") ? (
                    <span className="badge badge-warn"> low</span>
                  ) : null}
                </td>
                <td className="num">{value(player.rating)}</td>
                <td className="num">{percentile(player.rating_percentile)}</td>
                <td className="num">{percentile(player.adjusted_percentile)}</td>
                <td className="num">{value(player.display_value_index, 1)}</td>
                <td className="num">{value(player.priority, 1)}</td>
                <td>
                  {europeLabel(player)}
                  {qualifiesForEurope(player, weights.europe_minutes_threshold) ? (
                    <span className="badge badge-warn"> shop window</span>
                  ) : null}
                </td>
                <td className="num">{value(player.goals_assists_p90)}</td>
                <td className="num">{value(player.dribbles_success_p90)}</td>
                <td className="num">{value(player.passes_completed_p90)}</td>
                <td className="num">{percentage(player.pass_completion_pct)}</td>
                <td className="num">{value(player.key_passes_p90)}</td>
                <td className="num">{value(player.tackles_p90)}</td>
                <td className="num">{value(player.interceptions_p90)}</td>
                <td className="num">{percentage(player.duel_win_pct)}</td>
                <td>
                  {player.profile
                    ? `${player.profile.label} ${formatDecimal(player.profile.score, 1)}`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableFrame>
      {visible.length < filtered.length ? (
        <p>
          <button className="button button-ghost" onClick={() => setLimit(limit + 100)}>
            Show more players
          </button>
        </p>
      ) : null}
      {filtered.length === 0 ? (
        <p className="muted">No player matches these filters. Widen the league, role or minutes filter.</p>
      ) : null}
    </div>
  );
}
