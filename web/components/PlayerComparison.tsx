"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ComparisonDocument,
  ScoutingSearchMeta,
  ScoutingSearchRow,
  ScoutingSquadRow,
} from "@/lib/data";
import {
  comparisonGuard,
  fromSearchRow,
  fromSquadRow,
  type ComparisonPlayer,
} from "@/lib/comparison";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";

type Slot = { source: "current" | "scouted"; playerId: number };
type Slots = { a?: Slot; b?: Slot };

function parseSlot(value: string | null): Slot | null {
  if (!value) return null;
  const [source, raw] = value.split(":", 2);
  const playerId = Number(raw);
  if (!Number.isInteger(playerId)) return null;
  if (source !== "current" && source !== "scouted") return null;
  return { source, playerId };
}

function slotValue(slot: Slot | undefined): string {
  return slot ? `${slot.source}:${slot.playerId}` : "";
}

function rateValue(value: number | null, unit: "%" | "/90"): string {
  if (value === null || value === undefined) return "—";
  return unit === "%" ? formatPercentValue(value, 1) : formatDecimal(value, 2);
}

function archetypeScore(player: ComparisonPlayer, id: string): number | null {
  return player.archetypes.find((item) => item.id === id)?.score ?? null;
}

export function PlayerComparison({
  currentPlayers,
  comparison,
  meta,
  shardPaths,
}: {
  currentPlayers: ScoutingSquadRow[];
  comparison: ComparisonDocument | null;
  meta: ScoutingSearchMeta;
  shardPaths: string[];
}) {
  const allowlist = useMemo(
    () => new Set((comparison?.players ?? []).map((row) => row.player_id)),
    [comparison],
  );
  const currentRows = useMemo(
    () => currentPlayers.filter((row) => allowlist.has(row.player_id)),
    [allowlist, currentPlayers],
  );
  const [slots, setSlots] = useState<Slots>({});
  const [active, setActive] = useState<"a" | "b">("a");
  const [query, setQuery] = useState("");
  const [scouted, setScouted] = useState<ScoutingSearchRow[]>([]);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const loadingRef = useRef(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    const next: Slots = {};
    const left = parseSlot(params.get("a"));
    const right = parseSlot(params.get("b"));
    if (left) next.a = left;
    if (right) next.b = right;
    setSlots(next);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (slots.a) params.set("a", slotValue(slots.a));
    if (slots.b) params.set("b", slotValue(slots.b));
    const hash = params.toString();
    window.history.replaceState(
      null,
      "",
      hash ? `#${hash}` : window.location.pathname,
    );
  }, [slots]);

  const loadShards = useCallback(async () => {
    if (loadingRef.current || loadState === "ready") return;
    loadingRef.current = true;
    setLoadState("loading");
    try {
      const responses = await Promise.all(
        shardPaths.map(async (path) => {
          const response = await fetch(path);
          if (!response.ok) throw new Error(`shard ${response.status}`);
          return (await response.json()) as { players?: ScoutingSearchRow[] };
        }),
      );
      setScouted(responses.flatMap((payload) => payload.players ?? []));
      setLoadState("ready");
    } catch {
      setLoadState("error");
    } finally {
      loadingRef.current = false;
    }
  }, [loadState, shardPaths]);

  // Resolve a deep-linked scouted player after the shards arrive.
  useEffect(() => {
    const needsScouted = [slots.a, slots.b].some(
      (slot) => slot?.source === "scouted",
    );
    if (needsScouted && loadState === "idle") void loadShards();
  }, [loadShards, loadState, slots]);

  const resolve = useCallback(
    (slot: Slot | undefined): ComparisonPlayer | null => {
      if (!slot) return null;
      if (slot.source === "current") {
        const row = currentRows.find((item) => item.player_id === slot.playerId);
        return row ? fromSquadRow(row) : null;
      }
      const row = scouted.find((item) => item.i === slot.playerId);
      return row ? fromSearchRow(row, meta) : null;
    },
    [currentRows, meta, scouted],
  );

  const left = resolve(slots.a);
  const right = resolve(slots.b);
  const guard = left && right ? comparisonGuard(left, right, meta) : null;

  const candidates = useMemo(() => {
    const text = query.trim().toLowerCase();
    if (!text) return [];
    const current = currentRows
      .filter((row) => row.name.toLowerCase().includes(text))
      .slice(0, 10)
      .map((row) => ({
        key: `current-${row.player_id}`,
        label: `${row.name} · current squad · ${row.role_label}`,
        slot: { source: "current" as const, playerId: row.player_id },
      }));
    const pool = scouted
      .filter(
        (row) =>
          row.n.toLowerCase().includes(text) ||
          (row.c ?? "").toLowerCase().includes(text),
      )
      .slice(0, 15)
      .map((row) => ({
        key: `scouted-${row.i}`,
        label: `${row.n} · ${row.c ?? "club unknown"} · ${meta.role_labels[row.rf ?? ""] ?? "role unknown"} · ${meta.leagues.find((league) => league.slug === row.l)?.name ?? row.l}`,
        slot: { source: "scouted" as const, playerId: row.i },
      }));
    return [...current, ...pool].slice(0, 20);
  }, [currentRows, meta, query, scouted]);

  const choose = (slot: Slot) => {
    setSlots((current) => ({ ...current, [active]: slot }));
    setActive(active === "a" ? "b" : "a");
    setQuery("");
  };

  const card = (player: ComparisonPlayer | null, slot: "a" | "b") => (
    <div className="comparison-card">
      <p className="eyebrow">Player {slot.toUpperCase()}</p>
      {player ? (
        <>
          <p className="comparison-name">
            <Link href={player.href}>{player.name}</Link>
            <span className="badge badge-neutral">
              {player.source === "squad" ? "Current squad" : "Scouted"}
            </span>
          </p>
          <p className="fine-print">
            {player.leagueLabel} · {player.roleLabel}
          </p>
          <dl className="definition-meta">
            <dt>Minutes</dt>
            <dd>{player.minutes === null ? "—" : formatInteger(player.minutes)}</dd>
            <dt>Provider rating</dt>
            <dd>{player.rating === null ? "—" : formatDecimal(player.rating, 2)}</dd>
            <dt>Percentile</dt>
            <dd>
              {player.percentile === null
                ? "—"
                : formatPercentValue(player.percentile, 1)}
            </dd>
            <dt>Cohort</dt>
            <dd>
              {player.cohortBasis ?? "unknown basis"} · n{" "}
              {player.cohortN === null ? "—" : formatInteger(player.cohortN)}
            </dd>
          </dl>
        </>
      ) : (
        <p className="fine-print">
          {slots[slot]
            ? slots[slot]?.source === "current"
              ? "This player is not in the reviewed comparison crosswalk."
              : loadState === "loading" || loadState === "idle"
                ? "Loading the scouted pool…"
                : loadState === "error"
                  ? "The scouted pool could not be loaded."
                  : "No published scouting row matches that id."
            : "Not selected."}
        </p>
      )}
      <button
        type="button"
        className={active === slot ? "button" : "button button-ghost"}
        onClick={() => setActive(slot)}
      >
        {active === slot ? "Choosing for this slot" : `Choose player ${slot.toUpperCase()}`}
      </button>
    </div>
  );

  return (
    <section
      className="section comparison"
      id="compare"
      data-contract="scouting.search.comparison"
    >
      <div className="section-head">
        <div>
          <p className="eyebrow">Head to head</p>
          <h2>Guarded comparison</h2>
        </div>
        <span className="badge badge-neutral">Same league and role only</span>
      </div>
      <p>
        Compare two published profiles only when they share a league and a role
        family. The panel shows the published values side by side; it does not
        declare a winner, a ranking or a recommendation. Current-squad players
        appear only when a reviewed crosswalk row exists.{" "}
        <Link className="text-link" href="/glossary/#def-percentile">
          Percentile
        </Link>{" "}
        is within the stated cohort.
      </p>
      <div className="board-controls">
        <label>
          Find a player (current or scouted)
          <input
            type="search"
            value={query}
            placeholder="Name or club"
            onChange={(event) => {
              setQuery(event.target.value);
              if (event.target.value.trim() && loadState === "idle") void loadShards();
            }}
          />
        </label>
        {loadState === "idle" ? (
          <button type="button" className="button button-ghost" onClick={() => void loadShards()}>
            Load scouted pool
          </button>
        ) : null}
        {loadState === "loading" ? (
          <span className="badge badge-neutral">Loading scouted pool…</span>
        ) : null}
        {loadState === "error" ? (
          <span className="badge badge-warn">
            The scouted pool could not be loaded; current-squad comparisons remain available.
          </span>
        ) : null}
        <button
          type="button"
          className="button button-ghost"
          onClick={() => setSlots({})}
          disabled={!slots.a && !slots.b}
        >
          Clear
        </button>
      </div>
      {query.trim() ? (
        <ul className="plain-list comparison-candidates">
          {candidates.length ? (
            candidates.map((candidate) => (
              <li key={candidate.key}>
                <button
                  type="button"
                  className="link-button"
                  onClick={() => choose(candidate.slot)}
                >
                  {candidate.label}
                </button>
              </li>
            ))
          ) : (
            <li className="muted">
              {loadState === "loading"
                ? "Loading the scouted pool…"
                : "No published player matches that search."}
            </li>
          )}
        </ul>
      ) : null}

      <div className="comparison-grid">
        {card(left, "a")}
        {card(right, "b")}
      </div>

      {left && right ? (
        guard?.comparable ? (
          <>
            <p className="fine-print">
              Comparable: same league and role family, both with a published
              percentile and a cohort at or above the published minimum. Differences
              are shown; no winner is declared.
            </p>
            <div className="grid two-col">
              <div className="table-wrap">
                <table className="league-table compact">
                  <caption className="fine-print">
                    Published rates per 90 or percentage, side by side. No delta is
                    shown.
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Rate</th>
                      <th scope="col">{left.name}</th>
                      <th scope="col">{right.name}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {left.rates.map((rate) => (
                      <tr key={rate.id}>
                        <td>
                          {rate.label} ({rate.unit})
                        </td>
                        <td>{rateValue(rate.value, rate.unit)}</td>
                        <td>
                          {rateValue(
                            right.rates.find((item) => item.id === rate.id)?.value ??
                              null,
                            rate.unit,
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="league-table compact">
                  <caption className="fine-print">
                    Published profile scores side by side. Coverage is not shown as
                    a rating.
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Profile</th>
                      <th scope="col">{left.name}</th>
                      <th scope="col">{right.name}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {left.archetypes.map((archetype) => (
                      <tr key={archetype.id}>
                        <td>{archetype.label}</td>
                        <td>
                          {archetype.score === null
                            ? "—"
                            : formatDecimal(archetype.score, 1)}
                        </td>
                        <td>
                          {archetypeScore(right, archetype.id) === null
                            ? "—"
                            : formatDecimal(
                                archetypeScore(right, archetype.id) ?? 0,
                                1,
                              )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          <p className="fine-print" data-contract-indicator="unknown">
            Not comparable: {guard?.reason} The two players are not placed on a
            different scale.
          </p>
        )
      ) : (
        <p className="fine-print">
          Choose two players with the search above. A scouted player loads from the
          existing lazy shards; no extra index is embedded in this page.
        </p>
      )}
    </section>
  );
}
