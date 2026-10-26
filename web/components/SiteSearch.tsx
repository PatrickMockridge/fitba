"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { ReaderEntity, ScoutedEntity } from "@/lib/data";

const GROUP_ORDER = [
  "page",
  "match",
  "player",
  "former-player",
  "club",
  "staff",
  "season",
  "claim",
  "scouted-player",
];

const GROUP_LABEL: Record<string, string> = {
  page: "Pages",
  match: "Matches",
  player: "Current players",
  "former-player": "Former players",
  club: "Clubs",
  staff: "Staff",
  season: "Seasons",
  claim: "Claims",
  "scouted-player": "Scouted players",
};

type SearchResult = {
  key: string;
  name: string;
  href: string;
  group: string;
  context: string | null;
};

function fromEntity(entity: ReaderEntity): SearchResult {
  return {
    key: entity.entity_id,
    name: entity.name,
    href: entity.href ?? "",
    group: entity.search_group ?? entity.type,
    context: null,
  };
}

function fromScouted(entity: ScoutedEntity): SearchResult {
  return {
    key: `player:api:player:${entity.i}`,
    name: entity.n,
    href: entity.h,
    group: "scouted-player",
    context: [entity.l, entity.rf].filter(Boolean).join(" · ") || null,
  };
}

function match(result: SearchResult, query: string, aliases: string[]): boolean {
  if (!query) return true;
  const haystack = [result.name, ...aliases].join(" ").toLowerCase();
  return haystack.includes(query);
}

export function SiteSearch({
  entities,
  scoutedPath,
}: {
  entities: ReaderEntity[];
  scoutedPath: string;
}) {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("all");
  const [includeScouted, setIncludeScouted] = useState(false);
  const [scouted, setScouted] = useState<ScoutedEntity[]>([]);
  const [scoutedState, setScoutedState] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    setQuery(params.get("q") ?? "");
    setGroup(params.get("group") ?? "all");
    setIncludeScouted(params.get("scouting") === "1");
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (group !== "all") params.set("group", group);
    if (includeScouted) params.set("scouting", "1");
    const hash = params.toString();
    window.history.replaceState(null, "", hash ? `#${hash}` : window.location.pathname);
  }, [query, group, includeScouted]);

  useEffect(() => {
    if (group === "scouted-player") setIncludeScouted(true);
  }, [group]);

  useEffect(() => {
    if (!includeScouted || scoutedState !== "idle") return;
    setScoutedState("loading");
    fetch(scoutedPath)
      .then((response) => {
        if (!response.ok) throw new Error(`scouted index ${response.status}`);
        return response.json() as Promise<{ entities?: ScoutedEntity[] }>;
      })
      .then((payload) => {
        setScouted(payload.entities ?? []);
        setScoutedState("ready");
      })
      .catch(() => setScoutedState("error"));
  }, [includeScouted, scoutedPath, scoutedState]);

  const core = useMemo(
    () => entities.filter((entity) => entity.indexable && entity.href).map(fromEntity),
    [entities],
  );
  const all = useMemo(
    () => [...core, ...scouted.map(fromScouted)],
    [core, scouted],
  );
  const normalized = query.trim().toLowerCase();
  const filtered = useMemo(() => {
    const aliasesByKey = new Map(
      entities.map((entity) => [entity.entity_id, entity.aliases ?? []]),
    );
    for (const entity of scouted) {
      aliasesByKey.set(`player:api:player:${entity.i}`, entity.a ?? []);
    }
    return all
      .filter((result) => group === "all" || result.group === group)
      .filter((result) => match(result, normalized, aliasesByKey.get(result.key) ?? []));
  }, [all, group, normalized, entities, scouted]);

  const grouped = useMemo(() => {
    const output = new Map<string, SearchResult[]>();
    for (const result of filtered) {
      const rows = output.get(result.group) ?? [];
      rows.push(result);
      output.set(result.group, rows);
    }
    return [...output.entries()]
      .sort(([left], [right]) => GROUP_ORDER.indexOf(left) - GROUP_ORDER.indexOf(right))
      .map(([key, rows]) => [
        key,
        rows.sort((left, right) => left.name.localeCompare(right.name)).slice(0, 50),
      ] as const);
  }, [filtered]);

  const total = filtered.length;
  const showing = grouped.reduce((sum, [, rows]) => sum + rows.length, 0);

  return (
    <div className="site-search">
      <div className="board-controls">
        <label>
          Search
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Player, match, club, page or claim"
            autoFocus
          />
        </label>
        <label>
          Group
          <select value={group} onChange={(event) => setGroup(event.target.value)}>
            <option value="all">All groups</option>
            {GROUP_ORDER.map((key) => (
              <option key={key} value={key}>
                {GROUP_LABEL[key]}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={includeScouted}
            onChange={(event) => setIncludeScouted(event.target.checked)}
          />
          Include scouted players
        </label>
      </div>

      <p className="fine-print" aria-live="polite">
        A flat index of published pages and records. It is not ranked by popularity
        and it is not a transfer list.{" "}
        {includeScouted && scoutedState === "loading" ? "Loading the scouted pool. " : null}
        {includeScouted && scoutedState === "error"
          ? "The scouted pool could not be loaded; core results remain available. "
          : null}
        {normalized || group !== "all"
          ? `Showing ${showing} of ${total} matches.`
          : `${core.length} core records indexed.`}
      </p>

      {normalized || group !== "all" ? (
        grouped.length ? (
          <div className="search-groups">
            {grouped.map(([key, rows]) => (
              <section key={key} className="card">
                <p className="eyebrow">{GROUP_LABEL[key] ?? key}</p>
                <h2>{GROUP_LABEL[key] ?? key}</h2>
                <ul className="plain-list">
                  {rows.map((result) => (
                    <li key={result.key}>
                      <Link href={result.href}>{result.name}</Link>
                      {result.context ? (
                        <span className="muted"> · {result.context}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
                {filtered.filter((result) => result.group === key).length > rows.length ? (
                  <p className="fine-print">Refine the search to see more in this group.</p>
                ) : null}
              </section>
            ))}
          </div>
        ) : (
          <p className="muted">No published record matches that search.</p>
        )
      ) : (
        <div className="grid two-col">
          <section className="card">
            <p className="eyebrow">Start here</p>
            <h2>Type a name or a fixture</h2>
            <p>
              The search covers pages, matches, current players, former players, clubs,
              staff, seasons and claims. Scouted players load separately so the first
              page stays small.
            </p>
          </section>
          <section className="card">
            <p className="eyebrow">Groups</p>
            <h2>Published record types</h2>
            <ul className="plain-list">
              {GROUP_ORDER.map((key) => (
                <li key={key}>
                  <button type="button" className="link-button" onClick={() => setGroup(key)}>
                    {GROUP_LABEL[key]}
                  </button>
                  <span className="muted">
                    {" "}
                    ·{" "}
                    {key === "scouted-player"
                      ? scoutedState === "ready"
                        ? scouted.length
                        : scoutedState === "error"
                          ? "not loaded"
                          : "loads on request"
                      : entities.filter(
                          (entity) => (entity.search_group ?? entity.type) === key,
                        ).length}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
