"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { FormerPlayer, FormerPlayersFile } from "@/lib/data";
import { formatDate, formatInteger } from "@/lib/format";

type Filters = {
  query: string;
  season: string;
  kind: string;
  fee: string;
  market: string;
  coverage: string;
  rival: boolean;
  developed: boolean;
  sellOn: boolean;
};

const DEFAULT_FILTERS: Filters = {
  query: "",
  season: "all",
  kind: "all",
  fee: "all",
  market: "all",
  coverage: "all",
  rival: false,
  developed: false,
  sellOn: false,
};

function text(value: string | null | undefined): string {
  return value && value.length ? value : "—";
}

function number(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : formatInteger(value);
}

function currentLabel(player: FormerPlayer): string {
  const current = player.post_career.current;
  if (!current.club_name) return "Unknown";
  if (current.coverage === "current") return current.club_name;
  if (current.coverage === "historical") return `Last known: ${current.club_name}`;
  return current.club_name;
}

function statusLabel(player: FormerPlayer): string {
  const current = player.post_career.current;
  const label = current.status.replace("_", " ");
  return current.coverage === "current" ? label : `${label} · historical`;
}

function rivalLabel(player: FormerPlayer): string {
  if (player.post_career.rival_current) return "At rival now";
  if (player.post_career.at_rival) return "Rival spell";
  return "—";
}

function rowMatches(player: FormerPlayer, filters: Filters): boolean {
  const needle = filters.query.trim().toLowerCase();
  if (
    needle &&
    !`${player.name} ${player.position ?? ""} ${player.departure.to_club_name ?? ""} ${
      player.post_career.current.club_name ?? ""
    }`
      .toLowerCase()
      .includes(needle)
  ) {
    return false;
  }
  if (filters.season !== "all" && player.departure.season !== filters.season) return false;
  if (filters.kind !== "all" && player.departure.kind !== filters.kind) return false;
  if (filters.fee !== "all" && player.departure.fee_status !== filters.fee) return false;
  if (filters.market !== "all" && player.departure.to_market !== filters.market) return false;
  if (filters.coverage !== "all" && player.post_career.current.coverage !== filters.coverage) {
    return false;
  }
  if (filters.rival && !player.post_career.at_rival) return false;
  if (filters.developed && player.aberdeen.developed_here !== "yes") return false;
  if (filters.sellOn && !player.sell_on_clause_id) return false;
  return true;
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))].sort();
}

export function FormerPlayersBoard({ data }: { data: FormerPlayersFile }) {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const filtered = useMemo(
    () => data.players.filter((player) => rowMatches(player, filters)),
    [data.players, filters],
  );

  const seasonsOptions = unique(data.players.map((player) => player.departure.season));
  const kindOptions = unique(data.players.map((player) => player.departure.kind));
  const feeOptions = unique(data.players.map((player) => player.departure.fee_status));
  const marketOptions = unique(data.players.map((player) => player.departure.to_market));

  const update = <K extends keyof Filters>(key: K, value: Filters[K]) =>
    setFilters((current) => ({ ...current, [key]: value }));

  return (
    <section data-contract="former.board">
      <div className="board-controls">
        <label>
          Search
          <input
            type="search"
            value={filters.query}
            placeholder="Name, club or role"
            onChange={(event) => update("query", event.target.value)}
          />
        </label>
        <label>
          Exit season
          <select value={filters.season} onChange={(event) => update("season", event.target.value)}>
            <option value="all">All seasons</option>
            {seasonsOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          Exit type
          <select value={filters.kind} onChange={(event) => update("kind", event.target.value)}>
            <option value="all">All types</option>
            {kindOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          Fee status
          <select value={filters.fee} onChange={(event) => update("fee", event.target.value)}>
            <option value="all">All fee states</option>
            {feeOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          Destination
          <select value={filters.market} onChange={(event) => update("market", event.target.value)}>
            <option value="all">All markets</option>
            {marketOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          Current coverage
          <select
            value={filters.coverage}
            onChange={(event) => update("coverage", event.target.value)}
          >
            <option value="all">All coverage</option>
            <option value="current">Current season</option>
            <option value="historical">Last known</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
        <label className="check-line">
          <input
            type="checkbox"
            checked={filters.rival}
            onChange={(event) => update("rival", event.target.checked)}
          />
          Rival spell only
        </label>
        <label className="check-line">
          <input
            type="checkbox"
            checked={filters.developed}
            onChange={(event) => update("developed", event.target.checked)}
          />
          Early-career proxy only
        </label>
        <label className="check-line">
          <input
            type="checkbox"
            checked={filters.sellOn}
            onChange={(event) => update("sellOn", event.target.checked)}
          />
          Sell-on clause only
        </label>
      </div>

      <p className="fine-print" aria-live="polite">
        {filtered.length} of {data.players.length} former players in this view. Current club is
        labelled last known when the provider has no current-season row. A rival badge is a club
        fact, not a verdict on the player.
      </p>

      <div className="table-wrap">
        <table className="league-table compact" data-contract="former.register">
          <caption className="fine-print">
            Former players from 2019-20 onward. Exit fee is disclosed, reported or modelled, never
            zero; post-career totals cover covered league seasons only. The table is a register,
            not a list of transfer targets.
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Left</th>
              <th scope="col">To</th>
              <th scope="col">Type</th>
              <th scope="col">Fee</th>
              <th className="num" scope="col">Age</th>
              <th className="num" scope="col">Aberdeen apps</th>
              <th className="num" scope="col">Aberdeen starts</th>
              <th className="num" scope="col">Post seasons</th>
              <th className="num" scope="col">Post mins</th>
              <th scope="col">Current club</th>
              <th scope="col">Rival</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((player) => {
              const anchor = player.href.split("#")[1];
              return (
                <tr key={player.player_key} id={anchor} data-contract="former.row">
                  <td>
                    {player.player_id ? (
                      <Link
                        href={`/scouting/player/${player.player_id}/`}
                        className="text-link"
                      >
                        {player.name}
                      </Link>
                    ) : (
                      <span title="No API player id; no scouting profile is available.">
                        {player.name}
                      </span>
                    )}
                    {player.sell_on_clause_id ? (
                      <span className="badge badge-neutral"> sell-on</span>
                    ) : null}
                  </td>
                  <td>{formatDate(player.departure.date)}</td>
                  <td>{text(player.departure.to_club_name)}</td>
                  <td>{player.departure.kind}</td>
                  <td>{player.departure.fee_display}</td>
                  <td className="num">{player.age_at_exit ?? "—"}</td>
                  <td className="num">{number(player.aberdeen.appearances)}</td>
                  <td className="num">{number(player.aberdeen.starts)}</td>
                  <td className="num">
                    {player.post_career.totals.seasons_with_data}/
                    {player.post_career.totals.seasons_expected}
                  </td>
                  <td className="num">{number(player.post_career.totals.minutes)}</td>
                  <td>{currentLabel(player)}</td>
                  <td>
                    <span
                      className={
                        player.post_career.rival_current
                          ? "badge badge-warn"
                          : player.post_career.at_rival
                            ? "badge badge-neutral"
                            : "badge badge-neutral"
                      }
                    >
                      {rivalLabel(player)}
                    </span>
                  </td>
                  <td>
                    <span
                      className={
                        player.post_career.current.coverage === "current"
                          ? "badge badge-ok"
                          : player.post_career.current.coverage === "historical"
                            ? "badge badge-warn"
                            : "badge badge-neutral"
                      }
                    >
                      {statusLabel(player)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 ? <p className="muted">No former players match these filters.</p> : null}

    </section>
  );
}
