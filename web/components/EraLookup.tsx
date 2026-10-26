"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

export type EraLookupSeason = {
  season: string;
  status: "completed" | "in_progress";
  href: string;
  competition_name: string | null;
  headline: string;
  honour_ids: string[];
  manager_ids: string[];
};

export type EraLookupHonour = {
  id: string;
  label: string;
  season: string;
};

export type EraLookupManager = {
  id: string;
  name: string;
};

const FIELDS = ["season", "manager", "honour", "competition"] as const;

export function EraLookup({
  seasons,
  managers,
  honours,
}: {
  seasons: EraLookupSeason[];
  managers: EraLookupManager[];
  honours: EraLookupHonour[];
}) {
  const [state, setState] = useState<Record<string, string>>({});

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    const next: Record<string, string> = {};
    for (const field of FIELDS) {
      const value = params.get(field);
      if (value) next[field] = value;
    }
    setState(next);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    for (const field of FIELDS) {
      if (state[field]) params.set(field, state[field]);
    }
    const hash = params.toString();
    window.history.replaceState(
      null,
      "",
      hash ? `#${hash}` : window.location.pathname,
    );
  }, [state]);

  const managerNames = useMemo(
    () => new Map(managers.map((manager) => [manager.id, manager.name])),
    [managers],
  );
  const honoures = useMemo(
    () => new Map(honours.map((honour) => [honour.id, honour.label])),
    [honours],
  );
  const competitions = useMemo(
    () =>
      Array.from(
        new Set(
          seasons
            .map((season) => season.competition_name)
            .filter((name): name is string => Boolean(name)),
        ),
      ).sort(),
    [seasons],
  );

  const results = useMemo(
    () =>
      seasons
        .filter((season) => !state.season || season.season === state.season)
        .filter(
          (season) =>
            !state.manager || season.manager_ids.includes(state.manager),
        )
        .filter(
          (season) => !state.honour || season.honour_ids.includes(state.honour),
        )
        .filter(
          (season) =>
            !state.competition ||
            season.competition_name === state.competition,
        ),
    [seasons, state],
  );

  const active = Object.values(state).some(Boolean);

  const set = (field: string, value: string) => {
    setState((current) => {
      const next = { ...current };
      if (value) next[field] = value;
      else delete next[field];
      return next;
    });
  };

  return (
    <section className="section" data-contract="history.lookup">
      <div className="section-head">
        <div>
          <p className="eyebrow">Look up the record</p>
          <h2>Cormack-era lookup</h2>
        </div>
        <span className="badge badge-neutral">Published records only</span>
      </div>
      <p>
        Filter the published season records by season, manager, honour or
        competition. The lookup navigates the existing record; it does not rank
        seasons, add a superlative or change a value.
      </p>
      <div className="board-controls">
        <label>
          Season
          <select
            value={state.season ?? ""}
            onChange={(event) => set("season", event.target.value)}
          >
            <option value="">Every season</option>
            {seasons.map((season) => (
              <option key={season.season} value={season.season}>
                {season.season}
              </option>
            ))}
          </select>
        </label>
        <label>
          Manager
          <select
            value={state.manager ?? ""}
            onChange={(event) => set("manager", event.target.value)}
          >
            <option value="">Every manager</option>
            {managers.map((manager) => (
              <option key={manager.id} value={manager.id}>
                {manager.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Honour
          <select
            value={state.honour ?? ""}
            onChange={(event) => set("honour", event.target.value)}
          >
            <option value="">Every honour</option>
            {honours.map((honour) => (
              <option key={honour.id} value={honour.id}>
                {honour.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Competition
          <select
            value={state.competition ?? ""}
            onChange={(event) => set("competition", event.target.value)}
          >
            <option value="">Every competition</option>
            {competitions.map((competition) => (
              <option key={competition} value={competition}>
                {competition}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="button button-ghost"
          onClick={() => setState({})}
          disabled={!active}
        >
          Reset
        </button>
      </div>
      <p className="fine-print" aria-live="polite">
        {active
          ? "Showing the seasons that match every active filter."
          : "No filter is active; every published season is listed."}
      </p>
      <div className="table-wrap">
        <table className="league-table">
          <caption className="fine-print">
            Matching seasons with their published manager, honour and headline.
          </caption>
          <thead>
            <tr>
              <th scope="col">Season</th>
              <th scope="col">Status</th>
              <th scope="col">Competition</th>
              <th scope="col">Manager(s)</th>
              <th scope="col">Honours</th>
              <th scope="col">Headline</th>
            </tr>
          </thead>
          <tbody>
            {results.length ? (
              results.map((season) => (
                <tr key={season.season}>
                  <td>
                    <Link href={season.href}>{season.season}</Link>
                  </td>
                  <td>
                    {season.status === "in_progress" ? "In progress" : "Completed"}
                  </td>
                  <td>{season.competition_name ?? "—"}</td>
                  <td>
                    {season.manager_ids.length
                      ? season.manager_ids
                          .map((id) => managerNames.get(id) ?? id)
                          .join(", ")
                      : "—"}
                  </td>
                  <td>
                    {season.honour_ids.length
                      ? season.honour_ids
                          .map((id) => honoures.get(id) ?? id)
                          .join(", ")
                      : "—"}
                  </td>
                  <td>{season.headline}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6}>
                  No published season matches every active filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
