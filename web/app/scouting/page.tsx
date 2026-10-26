import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { DefinitionTerm } from "@/components/DefinitionTerm";
import { PriorityProfiles } from "@/components/PriorityProfiles";
import { ScoutingArchetypes } from "@/components/ScoutingArchetypes";
import { ScoutingAttackers } from "@/components/ScoutingAttackers";
import { ScoutingCoverage } from "@/components/ScoutingCoverage";
import { ScoutingHubLenses } from "@/components/ScoutingHubLenses";
import { ScoutingLayerZeroTable } from "@/components/ScoutingLayerZero";
import { ScoutingLeagueIndex } from "@/components/ScoutingLeagueIndex";
import { ScoutingSquadTable } from "@/components/ScoutingSquadTable";
import { ScoutingTeamLens } from "@/components/ScoutingTeamLens";
import { ScoutingWeaknessTable } from "@/components/ScoutingWeaknessTable";
import { ScoutingWeightsCard } from "@/components/ScoutingWeights";
import { getNeeds, getScouting, getScoutingSearch } from "@/lib/data";
import { formatInteger, formatPercentValue } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/scouting/" },
  title: "Scouting board · fitba",
  description:
    "Aberdeen's squad gaps by role family, verified availability, player profiles and a licensed player search across the scouting universe.",
};

export default function ScoutingPage() {
  const scouting = getScouting();
  if (!scouting || scouting.state === "empty") {
    return (
      <ContractPage surface="scouting" state="empty">
        <section className="page-head" data-contract="scouting.hero">
          <p className="eyebrow">Recruitment · Scouting</p>
          <h1>The scouting board</h1>
          <p className="lede">
            No scouting data is published in this build. Run the pool and role backfill, then
            publish the derived record.
          </p>
        </section>
        <section className="empty-state" data-contract="scouting.empty">
          <p>
            The board needs provider season statistics and starting-XI lineups. Until they are
            ingested, no ranking is shown: an empty table would imply a measured zero.
          </p>
        </section>
      </ContractPage>
    );
  }

  const board = scouting.board;
  const coverage = scouting.coverage;
  const totals = coverage.totals;
  const search = getScoutingSearch();
  const needs = getNeeds();

  return (
    <ContractPage surface="scouting">
      <section className="page-head" data-contract="scouting.hero">
        <p className="eyebrow">Recruitment · Season {scouting.season}</p>
        <h1>The scouting board</h1>
        <p className="lede">
          Start with the players already at the club, then the{" "}
          <DefinitionTerm id="role_family">role families</DefinitionTerm> where the
          competitive record sits below the league cohort, then the profiles that would add
          options. Provider ratings are relative to a league and role; they are not a verdict.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/scouting/search/">
            Search all leagues
          </Link>
          <Link className="button button-ghost" href="/recruitment/">
            Off the pitch
          </Link>
          <Link className="button button-ghost" href="/squad/">
            Current squad
          </Link>
          <span className="badge badge-neutral">
            {formatInteger(totals.searchable ?? 0)}/{formatInteger(totals.leagues ?? 0)} leagues
            searchable
          </span>
          <span className="badge badge-warn">
            {formatInteger(totals.with_minutes_450 ?? 0)} ranked players
          </span>
        </div>
        {scouting.state === "stale" ? (
          <p className="fine-print" data-contract-indicator="freshness">
            Stale record: {scouting.stale_reason ?? "refresh needed"}. The last good documents
            are shown rather than a silently empty board.
          </p>
        ) : null}
      </section>

      <section className="section" data-contract="scouting.layer-zero">
        <div className="section-head">
          <div>
            <p className="eyebrow">Layer 0 · Internal first</p>
            <h2>The players already at the club</h2>
          </div>
          <span className="badge badge-neutral">Official AFC team news only</span>
        </div>
        <p>
          Injured and returning players are considered before the market. A verified first-
          choice absentee changes the reading of a weak family from a replacement to cover.
          Availability is never inferred from minutes, and an unverified name stays unknown.
        </p>
        <ScoutingLayerZeroTable items={scouting.layer_zero} />
        <p className="fine-print" data-contract-indicator="availability">
          {formatInteger(scouting.layer_zero.length)} verified availability{" "}
          {scouting.layer_zero.length === 1 ? "entry" : "entries"}. Current-season minutes are
          not fitness evidence. {formatInteger(totals.players ?? 0)} pool players remain
          unaffected by a verified absence.
        </p>
      </section>

      <section className="section" data-contract="scouting.weakness-board">
        <div className="section-head">
          <div>
            <p className="eyebrow">Layer 1 · Measured gaps</p>
            <h2>Where the squad sits below its cohort</h2>
          </div>
          <span className="badge badge-neutral">
            {formatInteger(board.summary.below_cohort ?? 0)} role families below
          </span>
        </div>
        <ScoutingWeaknessTable board={board} />
      </section>

      <section className="section" data-contract="scouting.archetypes">
        <div className="section-head">
          <div>
            <p className="eyebrow">Layer 2 · Profile options</p>
            <h2>What would add strength in depth</h2>
          </div>
          <span className="badge badge-warn">Profiles, not targets</span>
        </div>
        <p>
          Each profile is a weighted composite of stats the licensed feed supplies, scored
          within the league and role cohort. Missing features are removed and the remaining
          weights renormalised; a profile below the coverage floor is null, not zero.
        </p>
        {search ? (
          <ScoutingHubLenses
            archetypes={scouting.archetypes}
            attackers={scouting.attackers}
            teamLens={scouting.team_lens ?? null}
            priority={scouting.priority}
            searchMeta={{ ...search, players: [] }}
          />
        ) : (
          <>
            <ScoutingArchetypes
              archetypes={scouting.archetypes}
              priority={scouting.priority}
            />
            <ScoutingAttackers
              attackers={scouting.attackers}
              priority={scouting.priority}
            />
            {scouting.team_lens ? (
              <ScoutingTeamLens
                label={scouting.team_lens.label}
                definition={scouting.team_lens.definition}
                threshold={scouting.team_lens.threshold}
                leaders={scouting.team_lens.leaders}
                coverage={scouting.team_lens.coverage}
              />
            ) : null}
          </>
        )}
      </section>

      {needs ? <PriorityProfiles data={needs} /> : null}

      <section className="card" data-contract="scouting.weights">
        <ScoutingWeightsCard priority={scouting.priority} europe={scouting.europe_coverage} />
      </section>

      <section className="section" data-contract="scouting.league-index">
        <div className="section-head">
          <div>
            <p className="eyebrow">Search the pool</p>
            <h2>Every league in the configured universe</h2>
          </div>
          <span className="badge badge-neutral">
            {formatInteger(totals.searchable ?? 0)} searchable
          </span>
          <Link className="text-link" href="/scouting/search/">
            Search all leagues →
          </Link>
        </div>
        <ScoutingLeagueIndex leagues={scouting.leagues} />
      </section>

      <section className="section" data-contract="scouting.squad-profile">
        <div className="section-head">
          <div>
            <p className="eyebrow">Squad by role</p>
            <h2>Position-specific output</h2>
          </div>
          <span className="badge badge-neutral">
            {formatPercentValue(
              ((totals.role_players ?? 0) / Math.max(totals.players ?? 1, 1)) * 100,
              1,
            )}{" "}
            role coverage
          </span>
        </div>
        <p>
          Forwards are read through goal contributions, wide players through successful
          dribbles, midfielders through completed and key passes, and defenders through the
          same passing and retention measures. Forward-pass splits, carries and pressures are
          not in the feed. The value index is a scouting ordering, not a transfer value; a GBP
          band is deferred until a public-source anchor register is available.
        </p>
        <ScoutingSquadTable rows={scouting.squad} />
      </section>

      <section
        className="card"
        data-contract="scouting.coverage"
        data-contract-indicator="source"
      >
        <div className="card-head">
          <div>
            <p className="eyebrow">Coverage and limits</p>
            <h2>What the pool can and cannot support</h2>
          </div>
          <span className="badge badge-neutral">Derived · licensed feed</span>
        </div>
        <ScoutingCoverage
          totals={coverage.totals}
          knownGaps={coverage.known_gaps}
          sources={coverage.sources}
        />
      </section>

      <p className="back-link">
        <Link href="/recruitment/">← Off the pitch</Link>
        {" · "}
        <Link href="/squad/">Squad →</Link>
        {" · "}
        <Link href="/analysis/">Season overview →</Link>
        {" · "}
        <Link href="/methodology/">Method →</Link>
      </p>
    </ContractPage>
  );
}
