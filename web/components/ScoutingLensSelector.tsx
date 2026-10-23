"use client";

import type {
  ScoutingArchetypeDefinition,
  ScoutingPriorityConfig,
} from "@/lib/data";
import { formatDecimal, formatInteger } from "@/lib/format";

export function ScoutingLensSelector({
  priorityActive,
  onPriorityChange,
  u23Boost,
  setU23Boost,
  u23Only,
  setU23Only,
  europeDiscount,
  setEuropeDiscount,
  excludeEurope,
  setExcludeEurope,
  underperformingOnly,
  setUnderperformingOnly,
  archetype,
  setArchetype,
  role,
  setRole,
  league,
  setLeague,
  leagues,
  roles,
  archetypes,
  priority,
  isDefault = false,
  includeLeague = true,
}: {
  priorityActive: boolean;
  onPriorityChange: (active: boolean) => void;
  u23Boost: boolean;
  setU23Boost: (value: boolean) => void;
  u23Only: boolean;
  setU23Only: (value: boolean) => void;
  europeDiscount: boolean;
  setEuropeDiscount: (value: boolean) => void;
  excludeEurope: boolean;
  setExcludeEurope: (value: boolean) => void;
  underperformingOnly: boolean;
  setUnderperformingOnly: (value: boolean) => void;
  archetype: string;
  setArchetype: (value: string) => void;
  role: string;
  setRole: (value: string) => void;
  league: string;
  setLeague: (value: string) => void;
  leagues: Array<{ slug: string; name: string }>;
  roles: Array<[string, string]>;
  archetypes: ScoutingArchetypeDefinition[];
  priority: ScoutingPriorityConfig;
  isDefault?: boolean;
  includeLeague?: boolean;
}) {
  const u23Active = u23Boost || u23Only;
  const europeActive = europeDiscount || excludeEurope;
  const profileActive = archetype !== "all";
  const roleActive = role !== "all";
  const leagueActive = includeLeague && league !== "all";
  const activeCount = [
    priorityActive,
    u23Active,
    europeActive,
    underperformingOnly,
    profileActive,
    roleActive,
    leagueActive,
  ].filter(Boolean).length;
  const selectedProfile = archetypes.find((item) => item.id === archetype);
  const selectedRole = roles.find(([key]) => key === role);
  const selectedLeague = leagues.find((item) => item.slug === league);

  return (
    <div className="board-lenses" data-contract="scouting.lenses">
      <span className="board-lenses-label">Lenses</span>
      <div className="lens-chips" role="group" aria-label="Scouting lenses">
        <button
          type="button"
          className={`lens-chip${priorityActive ? " is-active" : ""}`}
          aria-pressed={priorityActive}
          onClick={() => onPriorityChange(!priorityActive)}
        >
          Priority rank
        </button>
        <button
          type="button"
          className={`lens-chip${u23Active ? " is-active" : ""}`}
          aria-pressed={u23Active}
          onClick={() => {
            const next = !u23Active;
            setU23Boost(next);
            setU23Only(false);
          }}
        >
          U23
        </button>
        <button
          type="button"
          className={`lens-chip${europeActive ? " is-active" : ""}`}
          aria-pressed={europeActive}
          onClick={() => {
            const next = !europeActive;
            setEuropeDiscount(next);
            setExcludeEurope(false);
          }}
        >
          Europe shop window
        </button>
        <button
          type="button"
          className={`lens-chip${underperformingOnly ? " is-active" : ""}`}
          aria-pressed={underperformingOnly}
          onClick={() => setUnderperformingOnly(!underperformingOnly)}
        >
          Struggling team
        </button>
        <button
          type="button"
          className={`lens-chip${profileActive ? " is-active" : ""}`}
          aria-pressed={profileActive}
          onClick={() => setArchetype(profileActive ? "all" : archetypes[0]?.id ?? "all")}
        >
          Profile
        </button>
        <button
          type="button"
          className={`lens-chip${roleActive ? " is-active" : ""}`}
          aria-pressed={roleActive}
          onClick={() => setRole(roleActive ? "all" : roles[0]?.[0] ?? "all")}
        >
          Role
        </button>
        {includeLeague ? (
          <button
            type="button"
            className={`lens-chip${leagueActive ? " is-active" : ""}`}
            aria-pressed={leagueActive}
            onClick={() => setLeague(leagueActive ? "all" : leagues[0]?.slug ?? "all")}
          >
            League
          </button>
        ) : null}
      </div>
      <div className="lens-configs">
        {u23Active ? (
          <>
            <span className="lens-effect">
              U23 ≤{formatInteger(priority.u23_max_age)} ×
              {formatDecimal(priority.u23_multiplier, 2)}
            </span>
            <label>
              <input
                type="checkbox"
                checked={u23Only}
                onChange={(event) => setU23Only(event.target.checked)}
              />{" "}
              Only U23
            </label>
          </>
        ) : null}
        {europeActive ? (
          <>
            <span className="lens-effect">
              Europe league phase ≥{formatInteger(priority.europe_minutes_threshold)} min ×
              {formatDecimal(priority.europe_multiplier, 2)}
            </span>
            <label>
              <input
                type="checkbox"
                checked={excludeEurope}
                onChange={(event) => setExcludeEurope(event.target.checked)}
              />{" "}
              Exclude 90+ Europe
            </label>
          </>
        ) : null}
        {underperformingOnly ? (
          <span className="lens-effect">Team PPG percentile ≤40</span>
        ) : null}
        {profileActive ? (
          <label>
            Profile
            <select value={archetype} onChange={(event) => setArchetype(event.target.value)}>
              {archetypes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {roleActive ? (
          <label>
            Role
            <select value={role} onChange={(event) => setRole(event.target.value)}>
              {roles.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {leagueActive ? (
          <label>
            League
            <select value={league} onChange={(event) => setLeague(event.target.value)}>
              {leagues.map((item) => (
                <option key={item.slug} value={item.slug}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      <span className="lens-effect" aria-live="polite">
        {isDefault
          ? `Published defaults · U23 ≤${formatInteger(priority.u23_max_age)} ×${formatDecimal(priority.u23_multiplier, 2)}; Europe ≥${formatInteger(priority.europe_minutes_threshold)} min ×${formatDecimal(priority.europe_multiplier, 2)}.`
          : activeCount === 0
            ? "No lens selected: the base pool only."
            : `${activeCount > 1 ? `Layered (${activeCount})` : "Single lens"} · ${[
                priorityActive ? "priority rank" : null,
                u23Active ? `U23${u23Only ? " only" : ""}` : null,
                europeActive ? `Europe${excludeEurope ? " excluded" : " discounted"}` : null,
                underperformingOnly ? "struggling team" : null,
                selectedProfile ? selectedProfile.label : null,
                selectedRole ? selectedRole[1] : null,
                selectedLeague ? selectedLeague.name : null,
              ]
                .filter(Boolean)
                .join(" + ")}. Filters intersect; U23 and Europe multiply priority.`}
      </span>
    </div>
  );
}
