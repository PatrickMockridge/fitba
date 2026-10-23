"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  ScoutingArchetypeDefinition,
  ScoutingPlayer,
  ScoutingPoolDocument,
} from "@/lib/data";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";

type SortKey =
  | "percentile"
  | "adjusted"
  | "value_index"
  | "rating"
  | "minutes"
  | "goals_assists"
  | "archetype";

const SORT_LABELS: Record<SortKey, string> = {
  percentile: "Rating percentile",
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

function sortValue(player: ScoutingPlayer, key: SortKey, archetype: string): number | null {
  if (key === "percentile") return player.rating_percentile;
  if (key === "adjusted") return player.adjusted_percentile;
  if (key === "value_index") return player.value_index;
  if (key === "rating") return player.rating;
  if (key === "minutes") return player.minutes;
  if (key === "goals_assists") return player.goals_assists_p90;
  return player.archetypes[archetype]?.score ?? null;
}

export function ScoutingBoard({
  document,
  archetypes,
}: {
  document: ScoutingPoolDocument;
  archetypes: ScoutingArchetypeDefinition[];
}) {
  const players = document.players;
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("all");
  const [archetype, setArchetype] = useState("all");
  const [minMinutes, setMinMinutes] = useState("450");
  const [maxAge, setMaxAge] = useState("all");
  const [sort, setSort] = useState<SortKey>("percentile");

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
    return players
      .filter((player) => {
        if (needle) {
          const haystack = `${player.name} ${player.full_name ?? ""} ${player.club}`.toLowerCase();
          if (!haystack.includes(needle)) return false;
        }
        if (role !== "all" && (player.role_family ?? "unknown") !== role) return false;
        if (archetype !== "all" && player.archetypes[archetype]?.score == null) return false;
        if (player.minutes < minimum) return false;
        if (ageLimit !== null && (player.age ?? 99) > ageLimit) return false;
        return true;
      })
      .sort((left, right) => {
        const leftValue = sortValue(left, sort, archetype);
        const rightValue = sortValue(right, sort, archetype);
        if (leftValue === null && rightValue === null) return 0;
        if (leftValue === null) return 1;
        if (rightValue === null) return -1;
        if (rightValue !== leftValue) return rightValue - leftValue;
        return right.minutes - left.minutes;
      });
  }, [players, query, role, archetype, minMinutes, maxAge, sort]);

  return (
    <div>
      <div className="board-controls">
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
          Profile
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
      <p className="fine-print" aria-live="polite">
        Showing {formatInteger(filtered.length)} of {formatInteger(players.length)} ranked
        players at {formatInteger(Number(minMinutes))}+ minutes. Pct is within{" "}
        {document.league.name} and the role cohort; Adj Pct maps that standing into the
        Premiership distribution. The value index is a scouting ordering, not a transfer value.
        {document.coverage.role_players} players have a starting-XI role.
      </p>
      <div className="table-wrap">
        <table className="league-table compact">
          <caption className="fine-print">
            Provider season statistics for {document.league.name}. Percentiles are league- and
            role-relative; the provider rating is not a verdict. A dash means the feed does not
            supply the value.
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Club</th>
              <th scope="col">Role</th>
              <th className="num" scope="col">Age</th>
              <th className="num" scope="col">Mins</th>
              <th className="num" scope="col">Rating</th>
              <th className="num" scope="col">Pct</th>
              <th className="num" scope="col">Adj Pct</th>
              <th className="num" scope="col">Value index</th>
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
                <td>{player.name}</td>
                <td>{player.club}</td>
                <td>
                  {player.role_label}
                  {player.flags.includes("role_unknown") ? (
                    <span className="badge badge-neutral"> role unknown</span>
                  ) : null}
                </td>
                <td className="num">{value(player.age, 0)}</td>
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
