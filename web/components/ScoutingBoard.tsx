"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ScoutingLensSelector } from "@/components/ScoutingLensSelector";
import type {
  ScoutingArchetypeDefinition,
  ScoutingPlayer,
  ScoutingPoolDocument,
  ScoutingPriorityConfig,
} from "@/lib/data";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";
import { priorityFor as priorityForValues } from "@/lib/scouting-filters";

type SortKey =
  | "priority"
  | "percentile"
  | "adjusted"
  | "value_index"
  | "rating"
  | "minutes"
  | "goals_assists"
  | "archetype"
  | "team_lift";

type Row = ScoutingPlayer & { priority: number | null };

const SORT_LABELS: Record<SortKey, string> = {
  priority: "Scouting priority",
  percentile: "Rating percentile",
  adjusted: "Adjusted percentile",
  value_index: "Value index",
  rating: "Provider rating",
  minutes: "Minutes",
  goals_assists: "Goals + assists /90",
  archetype: "Profile score",
  team_lift: "Team lift",
};

const EUROPE_LABELS: Record<string, string> = {
  "UEFA Champions League": "UCL",
  "UEFA Europa League": "UEL",
  "UEFA Conference League": "UECL",
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

function sortValue(player: Row, key: SortKey, archetype: string): number | null {
  if (key === "priority") return player.priority;
  if (key === "percentile") return player.rating_percentile;
  if (key === "adjusted") return player.adjusted_percentile;
  if (key === "value_index") return player.value_index;
  if (key === "rating") return player.rating;
  if (key === "minutes") return player.minutes;
  if (key === "goals_assists") return player.goals_assists_p90;
  if (key === "team_lift") return player.team_lift;
  return player.archetypes[archetype]?.score ?? null;
}

function europeLabel(player: ScoutingPlayer): string {
  if (player.european_status === "unknown") return "Unknown";
  if (player.european_status === "none") return "—";
  const competitions = player.european_league_phase_competitions
    .map((name) => EUROPE_LABELS[name] ?? name)
    .join("/");
  const minutes = player.european_league_phase_minutes ?? 0;
  return competitions ? `${competitions} · ${minutes}m` : `${minutes}m`;
}

export function ScoutingBoard({
  document,
  archetypes,
  priority,
}: {
  document: ScoutingPoolDocument;
  archetypes: ScoutingArchetypeDefinition[];
  priority?: ScoutingPriorityConfig;
}) {
  const players = document.players;
  const weights: ScoutingPriorityConfig = priority ?? {
    u23_max_age: 23,
    u23_multiplier: 1.3,
    europe_minutes_threshold: 90,
    europe_multiplier: 0.6,
  };
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("all");
  const [archetype, setArchetype] = useState("all");
  const [minMinutes, setMinMinutes] = useState("450");
  const [maxAge, setMaxAge] = useState("all");
  const [u23Boost, setU23Boost] = useState(true);
  const [u23Only, setU23Only] = useState(false);
  const [europeDiscount, setEuropeDiscount] = useState(true);
  const [excludeEurope, setExcludeEurope] = useState(false);
  const [underperformingOnly, setUnderperformingOnly] = useState(false);
  const [sort, setSort] = useState<SortKey>("priority");

  useEffect(() => {
    const hash = window.location.hash.replace("#", "");
    if (archetypes.some((item) => item.id === hash)) {
      setArchetype(hash);
      setSort("archetype");
    }
  }, [archetypes]);

  const roles = useMemo(() => {
    const seen = new Map<string, string>();
    for (const player of players) {
      const key = player.role_family ?? "unknown";
      if (!seen.has(key)) seen.set(key, player.role_label);
    }
    return Array.from(seen.entries()).sort((left, right) => left[1].localeCompare(right[1]));
  }, [players]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const minimum = Number(minMinutes);
    const ageLimit = maxAge === "all" ? null : Number(maxAge);
    const matched = players
      .filter((player) => {
        if (needle) {
          const haystack = `${player.name} ${player.full_name ?? ""} ${player.club}`.toLowerCase();
          if (!haystack.includes(needle)) return false;
        }
        if (role !== "all" && (player.role_family ?? "unknown") !== role) return false;
        if (archetype !== "all" && player.archetypes[archetype]?.score == null) return false;
        if (player.minutes < minimum) return false;
        if (ageLimit !== null && (player.age ?? 99) > ageLimit) return false;
        if (u23Only && (player.age === null || player.age > weights.u23_max_age)) {
          return false;
        }
        if (excludeEurope && player.european_status === "qualified") return false;
        if (underperformingOnly && !player.team_underperforming) return false;
        return true;
      })
      .map((player) => ({
        ...player,
        priority: priorityForValues(
          player.value_index,
          player.age,
          player.european_status,
          weights,
          {
            priorityActive: true,
            u23Boost,
            u23Only,
            europeDiscount,
            excludeEurope,
            underperformingOnly,
            archetype,
            role,
            league: "",
          },
        ),
      }));
    return matched.sort((left, right) => {
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
    role,
    archetype,
    minMinutes,
    maxAge,
    u23Boost,
    u23Only,
    europeDiscount,
    excludeEurope,
    underperformingOnly,
    sort,
    weights,
  ]);

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
          league="all"
          setLeague={() => {}}
          leagues={[]}
          roles={roles}
          archetypes={archetypes}
          priority={weights}
          includeLeague={false}
        />
        <label>
          Search
          <input
            type="search"
            value={query}
            placeholder="Name or club"
            onChange={(event) => setQuery(event.target.value)}
          />
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
        Showing {formatInteger(filtered.length)} of {formatInteger(players.length)} ranked players
        at {formatInteger(Number(minMinutes))}+ minutes. Priority = value index × U23 multiplier ×
        European league-phase multiplier. U23 ≤{formatInteger(weights.u23_max_age)} ×
        {formatDecimal(weights.u23_multiplier, 2)}; European league phase ≥
        {formatInteger(weights.europe_minutes_threshold)} min ×
        {formatDecimal(weights.europe_multiplier, 2)}. Preferences, not measured quality; unknown
        Europe is not discounted.
      </p>
      <div className="table-wrap">
        <table className="league-table compact">
          <caption className="fine-print">
            Provider season statistics for {document.league.name}. Pct is within this league and
            role; Adj Pct maps that standing into the Premiership distribution. The value index
            is not a transfer value; priority is a scouting preference. A dash means the feed does
            not supply the value.
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Club</th>
              <th scope="col">Team</th>
              <th className="num" scope="col">Lift</th>
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
            {filtered.map((player) => (
              <tr key={`${player.player_id}-${player.club}`}>
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
      {filtered.length === 0 ? (
        <p className="muted">No player matches these filters. Widen the minutes or role filter.</p>
      ) : null}
    </div>
  );
}
