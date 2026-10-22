"use client";

import Link from "next/link";
import { useId, useState } from "react";
import type { SearchEntry } from "@/lib/data";

export function MatchArchiveSearch({ entries }: { entries: SearchEntry[] }) {
  const [query, setQuery] = useState("");
  const listId = useId();
  const needle = query.trim().toLowerCase();
  const matches = needle
    ? entries
        .filter((entry) => `${entry.name} ${entry.slug}`.toLowerCase().includes(needle))
        .slice(0, 20)
    : [];

  return (
    <div className="mini-block" data-contract="matches.search">
      <label className="stat-label" htmlFor={listId}>
        Find a match
      </label>
      <input
        id={listId}
        className="search-input"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Opponent, competition or date"
        autoComplete="off"
      />
      <p className="fine-print" aria-live="polite">
        {needle
          ? `${matches.length}${matches.length === 20 ? "+" : ""} matching entries`
          : `${entries.length} matches indexed`}
      </p>
      {needle && matches.length ? (
        <ul className="plain-list" role="list">
          {matches.map((entry) => (
            <li key={entry.id}>
              <Link className="text-link" href={entry.href ?? "#"}>
                {entry.name}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
