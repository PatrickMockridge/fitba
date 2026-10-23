import Link from "next/link";
import { notFound } from "next/navigation";
import { ContractPage } from "@/components/ContractPage";
import { ScoutingBoard } from "@/components/ScoutingBoard";
import { getScouting, getScoutingCoverage, getScoutingPool } from "@/lib/data";
import { formatInteger, formatPercentValue } from "@/lib/format";

export const dynamicParams = false;

export function generateStaticParams() {
  const coverage = getScoutingCoverage();
  return (coverage?.leagues ?? []).map((league) => ({ league: league.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ league: string }>;
}) {
  const { league } = await params;
  const document = getScoutingPool(league);
  if (!document) return { title: "Scouting · fitba" };
  const title = `${document.league.name} player search · fitba`;
  const description = `Provider season statistics and within-league role percentiles for ${document.league.name}. ${document.coverage.rated} rated players; ${document.coverage.role_players} with a starting-XI role.`;
  return {
    title,
    description,
    alternates: { canonical: `/scouting/${document.league.slug}/` },
    openGraph: { title, description, type: "article" },
  };
}

export default async function ScoutingLeaguePage({
  params,
}: {
  params: Promise<{ league: string }>;
}) {
  const { league } = await params;
  const document = getScoutingPool(league);
  const hub = getScouting();
  if (!document) notFound();
  const archetypes = hub?.archetypes ?? [];
  const empty = document.players.length === 0;
  const noStats = document.state === "no_player_stats" || document.coverage.players === 0;

  return (
    <ContractPage surface="scouting-league" state={empty ? "empty" : "full"}>
      <section className="page-head" data-contract="scouting.league-hero">
        <p className="eyebrow">
          Scouting · {document.league.country || "Provider league"} · Season {document.season}
        </p>
        <h1>{document.league.name} player search</h1>
        <p className="lede">
          Provider season statistics for every ranked player in {document.league.name}, with
          rating percentiles within the league and role family. The table is a profile search,
          not a target list.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/scouting/">
            Scouting board
          </Link>
          <Link className="button button-ghost" href="/scouting/search/">
            Search all leagues
          </Link>
          <Link className="button button-ghost" href="/methodology/">
            Method
          </Link>
          <span className="badge badge-neutral">
            {formatInteger(document.coverage.rated)} rated ·{" "}
            {formatInteger(document.coverage.players)} in the pool
          </span>
          {document.state === "stale" ? (
            <span className="badge badge-warn">Stale · {document.stale_reason ?? "refresh needed"}</span>
          ) : null}
        </div>
      </section>

      {empty ? (
        <section className="card empty-state" data-contract="scouting.league-empty">
          {noStats ? (
            <>
              <h2>No player statistics in the licensed feed</h2>
              <p>
                The provider returns no current-season player statistics for{" "}
                {document.league.name}, so this league is not searchable on ratings. The gap
                is labelled, not filled with zeroes. The league remains in the scouting
                universe so the coverage is visible.
              </p>
            </>
          ) : (
            <>
              <h2>No ranked player at the minutes threshold</h2>
              <p>
                The feed carries {formatInteger(document.coverage.players)} player rows for{" "}
                {document.league.name}, but none reaches 450 minutes in this build. No
                percentile is published below the threshold; the rows are not shown as
                zeroes or as unranked names.
              </p>
            </>
          )}
          <Link className="text-link" href="/scouting/">
            See the coverage table →
          </Link>
        </section>
      ) : (
        <section className="section" data-contract="scouting.league-search">
          <div className="section-head">
            <div>
              <p className="eyebrow">Player search</p>
              <h2>Ranked players at 450+ minutes</h2>
            </div>
            <span className="badge badge-neutral">
              Role coverage{" "}
              {formatPercentValue(document.coverage.role_coverage * 100, 1)}
            </span>
          </div>
          <ScoutingBoard document={document} archetypes={archetypes} />
        </section>
      )}

      <section className="card" data-contract="scouting.league-coverage">
        <div className="card-head">
          <div>
            <p className="eyebrow">Coverage and limits</p>
            <h2>What the feed carries for this league</h2>
          </div>
          <span className="badge badge-neutral">Source · API-Football</span>
        </div>
        <div className="stat-row four">
          <div className="stat-tile">
            <span className="stat-label">Fixtures played</span>
            <span className="stat-value">
              {formatInteger(document.coverage.fixtures_played)}
            </span>
            <span className="stat-note">lineups requested for played fixtures</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Players with a role</span>
            <span className="stat-value">
              {formatInteger(document.coverage.role_players)}
            </span>
            <span className="stat-note">
              {formatPercentValue(document.coverage.role_coverage * 100, 1)} of the pool
            </span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">At 450+ minutes</span>
            <span className="stat-value">
              {formatInteger(document.coverage.with_minutes_450)}
            </span>
            <span className="stat-note">the ranked pool</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Rated</span>
            <span className="stat-value">{formatInteger(document.coverage.rated)}</span>
            <span className="stat-note">provider rating present</span>
          </div>
        </div>
        <p className="fine-print">{document.coverage.note}</p>
        <ul className="plain-list">
          {document.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <Link className="text-link" href="/scouting/">
          Back to the scouting board →
        </Link>
      </section>
    </ContractPage>
  );
}
