import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { DefinitionTerm } from "@/components/DefinitionTerm";
import { PlayerComparison } from "@/components/PlayerComparison";
import { ScoutingGlobalSearch } from "@/components/ScoutingGlobalSearch";
import {
  getComparison,
  getScouting,
  getScoutingSearch,
  SCOUTING_SEARCH_SHARDS,
} from "@/lib/data";
import { assetPath } from "@/lib/asset-path";
import { formatInteger } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/scouting/search/" },
  title: "Search the scouting pool · fitba",
  description:
    "Every ranked player in the licensed scouting pool, across every league, with within-league role percentiles and profiles.",
};

export default function ScoutingSearchPage() {
  const document = getScoutingSearch();
  const hub = getScouting();
  if (!document || document.state === "empty") {
    return (
      <ContractPage surface="scouting-search" state="empty">
        <section className="page-head" data-contract="scouting.search.hero">
          <p className="eyebrow">Recruitment · Scouting</p>
          <h1>Search the scouting pool</h1>
          <p className="lede">
            No searchable pool is published in this build. Run the scouting pool and role
            backfill, then publish the derived record.
          </p>
        </section>
        <section className="empty-state" data-contract="scouting.search.empty">
          <p>
            An empty table would imply a measured zero. Until the pool is ingested, the search
            stays explicitly unavailable.
          </p>
        </section>
      </ContractPage>
    );
  }
  const archetypes = hub?.archetypes ?? [];
  const leagues = document.leagues.filter((league) => league.players > 0);
  const initialPlayers = document.players.slice(0, 100);
  const documentMeta = { ...document, players: [] };
  const shardPaths = Array.from({ length: SCOUTING_SEARCH_SHARDS }, (_, shard) =>
    assetPath(`/scouting/search/shards/${shard}`),
  );
  const comparison = getComparison();

  return (
    <ContractPage surface="scouting-search">
      <section className="page-head" data-contract="scouting.search.hero">
        <p className="eyebrow">Recruitment · Season {document.season}</p>
        <h1>Search the full scouting pool</h1>
        <p className="lede">
          Every ranked player across every league the licensed feed supports:{" "}
          {formatInteger(document.count)} players in {formatInteger(leagues.length)} leagues.
          Filter by league, role, nationality, age, minutes or top profile. Percentiles are
          within each league and role; the table is not a cross-league ranking. The default
          sort is a league mix so every league is visible immediately; it is not a
          cross-league quality rank. The top-profile filter uses each
          player&apos;s strongest profile; the per-league page allows a profile-specific filter.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/scouting/">
            Scouting board
          </Link>
          <a className="button button-ghost" href="#compare">
            Compare players
          </a>
          <Link className="button button-ghost" href="/methodology/">
            Method
          </Link>
          <span className="badge badge-neutral">
            {formatInteger(document.count)} ranked players
          </span>
          <span className="badge badge-warn">
            {formatInteger(leagues.length)} leagues with rated players
          </span>
        </div>
      </section>

      <section className="section" data-contract="scouting.search.board">
        <div className="section-head">
          <div>
            <p className="eyebrow">Full search</p>
            <h2>One table, every league</h2>
          </div>
          <span className="badge badge-neutral" data-contract-indicator="confidence">
            Within-league percentiles
          </span>
        </div>
        <p>
          The league filter is the comparison boundary. A 90th{" "}
          <DefinitionTerm id="percentile">percentile</DefinitionTerm> in one league is
          not the same as a 90th percentile in another; the page shows both the league
          and the percentile so the comparison is never implied to cross that line.
        </p>
        <ScoutingGlobalSearch
          document={documentMeta}
          archetypes={archetypes}
          initialPlayers={initialPlayers}
          shardPaths={shardPaths}
        />
      </section>

      <PlayerComparison
        currentPlayers={hub?.squad ?? []}
        comparison={comparison}
        meta={documentMeta}
        shardPaths={shardPaths}
      />

      <section
        className="card"
        data-contract="scouting.search.coverage"
        data-contract-indicator="source"
      >
        <div className="card-head">
          <div>
            <p className="eyebrow">Coverage and limits</p>
            <h2>What the full search covers</h2>
          </div>
          <span className="badge badge-neutral">Source · API-Football</span>
        </div>
        <div className="stat-row four">
          <div className="stat-tile">
            <span className="stat-label">Ranked players</span>
            <span className="stat-value">{formatInteger(document.count)}</span>
            <span className="stat-note">
              at {formatInteger(document.min_minutes)}+ minutes
            </span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Leagues with players</span>
            <span className="stat-value">{formatInteger(leagues.length)}</span>
            <span className="stat-note">of the configured universe</span>
          </div>
          <div className="stat-tile" data-contract-indicator="unknown">
            <span className="stat-label">Leagues with no ranked player</span>
            <span className="stat-value">
              {formatInteger(
                document.leagues.filter((league) => league.players === 0).length,
              )}
            </span>
            <span className="stat-note">no player at 450+ minutes</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Cross-league ranking</span>
            <span className="stat-value">None</span>
            <span className="stat-note">league-relative percentiles only</span>
          </div>
        </div>
        <ul className="plain-list">
          {document.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="fine-print">
          See <Link href="/sources/">sources and licences</Link> and{" "}
          <Link href="/methodology/">the method</Link>. Raw provider responses are not
          published.
        </p>
        <Link className="text-link" href="/scouting/">
          Back to the scouting board →
        </Link>
      </section>
    </ContractPage>
  );
}
