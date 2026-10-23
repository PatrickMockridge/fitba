"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ScoutingArchetypes } from "@/components/ScoutingArchetypes";
import { ScoutingAttackers } from "@/components/ScoutingAttackers";
import { ScoutingLensSelector } from "@/components/ScoutingLensSelector";
import { ScoutingTeamLens } from "@/components/ScoutingTeamLens";
import type {
  ScoutingArchetypeDefinition,
  ScoutingAttackers as ScoutingAttackersDocument,
  ScoutingLeader,
  ScoutingPriorityConfig,
  ScoutingSearchDocument,
} from "@/lib/data";
import {
  buildPoolRows,
  defaultFilters,
  defaultLenses,
  defaultValueWeights,
  isDefaultLenses,
  readerArchetypes,
  readerAttackers,
  readerTeamLeaders,
  type ScoutingLenses,
  type ScoutingPoolRow,
  type ScoutingSession,
} from "@/lib/scouting-filters";

type TeamLensDocument = {
  label: string;
  definition: string;
  threshold: number | null;
  leaders: ScoutingLeader[];
  coverage: Record<string, number>;
};

type LoadStatus = "idle" | "loading" | "ready" | "error";

export function ScoutingHubLenses({
  archetypes,
  attackers,
  teamLens,
  priority,
  searchMeta,
}: {
  archetypes: ScoutingArchetypeDefinition[];
  attackers: ScoutingAttackersDocument;
  teamLens: TeamLensDocument | null;
  priority: ScoutingPriorityConfig;
  searchMeta: ScoutingSearchDocument;
}) {
  const [lenses, setLenses] = useState<ScoutingLenses>(defaultLenses);
  const [status, setStatus] = useState<LoadStatus>("idle");
  const [attempt, setAttempt] = useState(0);
  const [document, setDocument] = useState<ScoutingSearchDocument>(searchMeta);
  const [pool, setPool] = useState<ScoutingPoolRow[] | null>(null);
  const started = useRef(false);

  const isDefault = isDefaultLenses(lenses);
  const activePriority: ScoutingPriorityConfig = {
    ...priority,
    u23_multiplier: lenses.u23Boost ? priority.u23_multiplier : 1,
    europe_multiplier: lenses.europeDiscount ? priority.europe_multiplier : 1,
  };

  useEffect(() => {
    if (isDefault || pool || started.current) return;
    started.current = true;
    setStatus("loading");
    fetch("pool.json")
      .then((response) => {
        if (!response.ok) throw new Error(`pool.json ${response.status}`);
        return response.json() as Promise<ScoutingSearchDocument>;
      })
      .then((loaded) => {
        if (!loaded.players?.length || !loaded.profile_labels) {
          throw new Error("invalid pool document");
        }
        setDocument(loaded);
        setPool(buildPoolRows(loaded));
        setStatus("ready");
      })
      .catch(() => {
        setStatus("error");
      });
  }, [isDefault, pool, attempt]);

  const session = useMemo<ScoutingSession | null>(() => {
    if (!pool) return null;
    return {
      document,
      priority,
      lenses,
      filters: defaultFilters(document.min_minutes),
      valueWeights: defaultValueWeights(document),
      teamThreshold:
        document.team_context.underperforming_ppg_percentile_max,
      minLift: document.team_context.min_lift,
    };
  }, [pool, document, priority, lenses]);

  const reader = useMemo(() => {
    if (!session || !pool) return null;
    return {
      archetypes: readerArchetypes(archetypes, pool, session),
      attackers: readerAttackers(attackers, pool, session),
      teamLeaders: teamLens
        ? readerTeamLeaders(teamLens.leaders, pool, session)
        : [],
    };
  }, [session, pool, archetypes, attackers, teamLens]);

  const leagues = useMemo(
    () =>
      searchMeta.leagues
        .filter((league) => league.players > 0)
        .map((league) => ({ slug: league.slug, name: league.name }))
        .sort((left, right) => left.name.localeCompare(right.name)),
    [searchMeta.leagues],
  );
  const roles = useMemo(
    () =>
      Object.entries(searchMeta.role_labels).sort((left, right) =>
        left[1].localeCompare(right[1]),
      ),
    [searchMeta.role_labels],
  );

  const showReader = !isDefault && status === "ready" && reader !== null;

  return (
    <div>
      <div className="board-controls" data-contract="scouting.filters">
        <ScoutingLensSelector
          priorityActive={lenses.priorityActive}
          onPriorityChange={(active) =>
            setLenses((current) => ({ ...current, priorityActive: active }))
          }
          u23Boost={lenses.u23Boost}
          setU23Boost={(value) =>
            setLenses((current) => ({ ...current, u23Boost: value }))
          }
          u23Only={lenses.u23Only}
          setU23Only={(value) =>
            setLenses((current) => ({ ...current, u23Only: value }))
          }
          europeDiscount={lenses.europeDiscount}
          setEuropeDiscount={(value) =>
            setLenses((current) => ({ ...current, europeDiscount: value }))
          }
          excludeEurope={lenses.excludeEurope}
          setExcludeEurope={(value) =>
            setLenses((current) => ({ ...current, excludeEurope: value }))
          }
          underperformingOnly={lenses.underperformingOnly}
          setUnderperformingOnly={(value) =>
            setLenses((current) => ({ ...current, underperformingOnly: value }))
          }
          archetype={lenses.archetype}
          setArchetype={(value) =>
            setLenses((current) => ({ ...current, archetype: value }))
          }
          role={lenses.role}
          setRole={(value) =>
            setLenses((current) => ({ ...current, role: value }))
          }
          league={lenses.league}
          setLeague={(value) =>
            setLenses((current) => ({ ...current, league: value }))
          }
          leagues={leagues}
          roles={roles}
          archetypes={archetypes}
          priority={priority}
          isDefault={isDefault}
        />
        <button
          type="button"
          className="button button-ghost"
          onClick={() => setLenses(defaultLenses())}
          disabled={isDefault}
        >
          Reset to published defaults
        </button>
        <span
          className={`badge ${isDefault ? "badge-neutral" : "badge-warn"}`}
          aria-live="polite"
        >
          {isDefault ? "Published defaults" : "Reader scenario"}
        </span>
      </div>

      {status === "loading" ? (
        <p className="fine-print" aria-live="polite">
          Loading the full pool to apply the active lenses…
        </p>
      ) : null}
      {status === "error" ? (
        <p className="fine-print" role="status">
          The full pool could not be loaded, so the published lists are shown
          unchanged.{" "}
          <button
            type="button"
            className="button button-ghost"
            onClick={() => {
              started.current = false;
              setStatus("idle");
              setAttempt((current) => current + 1);
            }}
          >
            Retry
          </button>
        </p>
      ) : null}

      {showReader && reader ? (
        <>
          <ScoutingArchetypes
            archetypes={reader.archetypes}
            priority={activePriority}
            scenario
          />
          <ScoutingAttackers
            attackers={reader.attackers}
            priority={activePriority}
            scenario
          />
          {teamLens ? (
            <ScoutingTeamLens
              label={teamLens.label}
              definition={teamLens.definition}
              threshold={teamLens.threshold}
              leaders={reader.teamLeaders}
              coverage={teamLens.coverage}
              scenario
            />
          ) : null}
        </>
      ) : (
        <>
          <ScoutingArchetypes archetypes={archetypes} priority={activePriority} />
          <ScoutingAttackers attackers={attackers} priority={activePriority} />
          {teamLens ? (
            <ScoutingTeamLens
              label={teamLens.label}
              definition={teamLens.definition}
              threshold={teamLens.threshold}
              leaders={teamLens.leaders}
              coverage={teamLens.coverage}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
