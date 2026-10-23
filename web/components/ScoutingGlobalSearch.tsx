"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type {
  ScoutingArchetypeDefinition,
  ScoutingPriorityConfig,
  ScoutingSearchDocument,
} from "@/lib/data";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";

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
  | "archetype";

type Row = {
  player_id: number;
  name: string;
  club: string;
  stats_club: string;
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
};

function value(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? "—" : formatDecimal(value, digits);
}

function percentile(value: number | null): string {
  return value === null || value === undefined ? "—" : formatPercentValue(value, 1);
}

function percentage(value: number | null): string {
  return value === null || value === undefined ? "—" : formatPercentValue(value, 1);
}

function priorityFor(
  player: Row,
  weights: ScoutingPriorityConfig,
  u23Boost: boolean,
  europeDiscount: boolean,
): number | null {
  if (player.value_index === null) return null;
  const ageMultiplier =
    u23Boost && player.age !== null && player.age <= weights.u23_max_age
      ? weights.u23_multiplier
      : 1;
  const europeMultiplier =
    europeDiscount && player.european_status === "qualified"
      ? weights.europe_multiplier
      : 1;
  return player.value_index * ageMultiplier * europeMultiplier;
}

function sortValue(player: Row, key: SortKey, archetype: string): number | null {
  if (key === "priority") return player.priority;
  if (key === "percentile") return player.rating_percentile;
  if (key === "adjusted") return player.adjusted_percentile;
  if (key === "value_index") return player.value_index;
  if (key === "rating") return player.rating;
  if (key === "minutes") return player.minutes;
  if (key === "goals_assists") return player.goals_assists_p90;
  if (key === "archetype") return player.archetypes[archetype] ?? null;
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
}: {
  document: ScoutingSearchDocument;
  archetypes: ScoutingArchetypeDefinition[];
}) {
  const weights: ScoutingPriorityConfig = document.priority ?? {
    u23_max_age: 23,
    u23_multiplier: 1.3,
    europe_minutes_threshold: 90,
    europe_multiplier: 0.6,
  };
  const [query, setQuery] = useState("");
  const [league, setLeague] = useState("all");
  const [role, setRole] = useState("all");
  const [nationality, setNationality] = useState("all");
  const [archetype, setArchetype] = useState("all");
  const [minMinutes, setMinMinutes] = useState("450");
  const [maxAge, setMaxAge] = useState("all");
  const [u23Boost, setU23Boost] = useState(true);
  const [u23Only, setU23Only] = useState(false);
  const [europeDiscount, setEuropeDiscount] = useState(true);
  const [excludeEurope, setExcludeEurope] = useState(false);
  const [sort, setSort] = useState<SortKey>("priority");
  const [limit, setLimit] = useState(100);

  const leagueBySlug = useMemo(
    () => new Map(document.leagues.map((league) => [league.slug, league])),
    [document.leagues],
  );
  const players = useMemo<Row[]>(
    () =>
      document.players.map((row) => ({
        player_id: row.i,
        name: row.n,
        club: row.c,
        stats_club: row.sc ?? row.c,
        league_slug: row.l,
        league_name: leagueBySlug.get(row.l)?.name ?? row.l,
        nationality: row.na,
        role_family: row.rf,
        role_label: row.rf
          ? document.role_labels[row.rf] ?? "Role unknown"
          : "Role unknown",
        age: row.a,
        minutes: row.m,
        rating: row.rt,
        rating_percentile: row.p,
        adjusted_percentile: row.ap,
        value_index: row.vi,
        european_status: row.es ?? "unknown",
        european_minutes: row.em,
        european_competitions: row.eu ?? [],
        priority: null,
        goals_assists_p90: row.ga,
        dribbles_success_p90: row.dr,
        passes_completed_p90: row.ps,
        pass_completion_pct: row.pa,
        key_passes_p90: row.kp,
        tackles_p90: row.tk,
        interceptions_p90: row.it,
        duel_win_pct: row.dw,
        flags: row.f.map((code) => FLAG_CODES[code] ?? code),
        archetypes: row.ar ?? {},
        profile: row.pr
          ? {
              id: row.pr,
              label: document.profile_labels[row.pr] ?? row.pr,
              score: row.psc ?? 0,
            }
          : null,
      })),
    [document.players, document.role_labels, document.profile_labels, leagueBySlug],
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
    u23Boost,
    u23Only,
    europeDiscount,
    excludeEurope,
    sort,
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
        if (u23Only && (player.age === null || player.age > weights.u23_max_age)) {
          return false;
        }
        if (excludeEurope && player.european_status === "qualified") return false;
        return true;
      })
      .map((player) => ({
        ...player,
        priority: priorityFor(player, weights, u23Boost, europeDiscount),
      }));
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
    u23Boost,
    u23Only,
    europeDiscount,
    excludeEurope,
    sort,
    weights,
  ]);

  const visible = filtered.slice(0, limit);

  return (
    <div>
      <div className="board-controls">
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
          League
          <select value={league} onChange={(event) => setLeague(event.target.value)}>
            <option value="all">All leagues</option>
            {leagues.map((item) => (
              <option key={item.slug} value={item.slug}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Role
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="all">All roles</option>
            {roles.map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
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
          Top profile
          <select
            value={archetype}
            onChange={(event) => {
              setArchetype(event.target.value);
              if (event.target.value !== "all") setSort("archetype");
            }}
          >
            <option value="all">All profiles</option>
            {archetypes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Minimum minutes
          <select value={minMinutes} onChange={(event) => setMinMinutes(event.target.value)}>
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
          <input
            type="checkbox"
            checked={u23Boost}
            onChange={(event) => setU23Boost(event.target.checked)}
          />{" "}
          U23 boost
        </label>
        <label>
          <input
            type="checkbox"
            checked={u23Only}
            onChange={(event) => setU23Only(event.target.checked)}
          />{" "}
          U23 only
        </label>
        <label>
          <input
            type="checkbox"
            checked={europeDiscount}
            onChange={(event) => setEuropeDiscount(event.target.checked)}
          />{" "}
          Europe discount
        </label>
        <label>
          <input
            type="checkbox"
            checked={excludeEurope}
            onChange={(event) => setExcludeEurope(event.target.checked)}
          />{" "}
          Exclude 90+ Europe
        </label>
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
      <p className="fine-print" aria-live="polite" data-contract-indicator="basis">
        Showing {formatInteger(visible.length)} of {formatInteger(filtered.length)} matches from{" "}
        {formatInteger(players.length)} ranked players across {formatInteger(leagues.length)}{" "}
        leagues. Priority = value index × U23 multiplier × European league-phase multiplier.
        U23 ≤{formatInteger(weights.u23_max_age)} ×
        {formatDecimal(weights.u23_multiplier, 2)}; European league phase ≥
        {formatInteger(weights.europe_minutes_threshold)} min ×
        {formatDecimal(weights.europe_multiplier, 2)}. These are Aberdeen scouting preferences,
        not measured quality. Unknown Europe status is not discounted.
      </p>
      <div className="table-wrap">
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
                <td className="num">{value(player.value_index, 1)}</td>
                <td className="num">{value(player.priority, 1)}</td>
                <td>
                  {europeLabel(player)}
                  {player.european_status === "qualified" ? (
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
      </div>
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
