import type { Metadata } from "next";
import Link from "next/link";
import { BucketBars } from "@/components/BucketBars";
import { ContractPage } from "@/components/ContractPage";
import { FormerPlayerMentions } from "@/components/FormerPlayerMentions";
import { FormerPlayersBoard } from "@/components/FormerPlayersBoard";
import { ProfileSection } from "@/components/ProfileSection";
import { SellOnTable } from "@/components/SellOnTable";
import { StatTile } from "@/components/StatTile";
import {
  getFormerPlayers,
  getForumSignal,
  getRumours,
} from "@/lib/data";
import { formatDate, formatGbp, formatInteger } from "@/lib/format";

export const metadata: Metadata = {
  alternates: { canonical: "/former-players/" },
  title: "Former players · fitba",
  description:
    "Aberdeen former players from 2019-20: departure, Aberdeen record, post-Aberdeen league output, rival spells and sell-on watch.",
};

function bucket(
  data: Record<string, number | Record<string, number> | null>,
  key: string,
): Record<string, number> {
  const value = data[key];
  return value && typeof value === "object" ? (value as Record<string, number>) : {};
}

function count(
  data: Record<string, number | Record<string, number> | null>,
  key: string,
): number {
  const value = data[key];
  return typeof value === "number" ? value : 0;
}

export default function FormerPlayersPage() {
  const data = getFormerPlayers();
  const forum = getForumSignal();
  const rumours = getRumours();

  if (!data || data.state === "unavailable") {
    return (
      <ContractPage surface="former-players" state="empty">
        <section className="empty-state" data-contract="former.empty">
          <h1>Former-player record not published</h1>
          <p>
            Run <code>uv run fitba former-players backfill</code>, then{" "}
            <code>uv run fitba publish</code>. The page does not substitute a squad list or a
            transfer register for the post-Aberdeen record.
          </p>
        </section>
      </ContractPage>
    );
  }

  const cohorts = data.development_scorecard.cohorts;
  const currentLeagues = bucket(data.summary, "by_current_league");
  const currentStatus = bucket(data.summary, "by_current_status");
  const feeBasis = bucket(data.summary, "by_fee_basis");
  const summary = data.summary;

  return (
    <ContractPage surface="former-players">
      <section className="page-head" data-contract="former.hero">
        <p className="eyebrow">Aberdeen · former players · Season {data.season}</p>
        <h1>Former players</h1>
        <p className="lede">
          Every confirmed permanent or free departure from 2019-20 onward, with the Aberdeen
          record, the league seasons that followed and the public evidence around the sale. A
          former player is not a transfer target. This is not a full all-time list: earlier
          departures sit outside the confirmed register.
        </p>
        <div className="hero-actions">
          <span className="badge badge-ok">{formatInteger(data.players.length)} players</span>
          <span className="badge badge-neutral">
            {formatInteger(Number(summary.sell_on_clauses ?? 0))} sell-on clauses
          </span>
          <span className="badge badge-warn">
            {formatInteger(Number(summary.rival_spell ?? 0))} with a rival spell
          </span>
          <span className="badge badge-neutral">state: {data.state}</span>
          {data.served_generated_at ? (
            <span className="badge badge-warn">
              last served {formatDate(data.served_generated_at.slice(0, 10))}
            </span>
          ) : null}
        </div>
        <p className="fine-print" data-contract-indicator="source">
          Register from {data.coverage.register_from}. Post-career league seasons from
          API-Football; missing seasons are gaps, not zero. Cup and European provider rows are
          excluded from totals because some repeat league totals.
        </p>
      </section>

      <ProfileSection
        eyebrow="Summary"
        title="What the register contains"
        badge={`${data.coverage.counts.with_post_career_rows ?? 0} with post-Aberdeen league data`}
        note={data.coverage.note}
        indicator="unknown"
        contract="former.summary"
      >
        <div className="stat-row four">
          <StatTile
            label="Permanent exits"
            value={formatInteger(bucket(data.summary, "by_exit_kind").permanent ?? 0)}
            note="permanent/free universe"
          />
          <StatTile
            label="Free exits"
            value={formatInteger(bucket(data.summary, "by_exit_kind").free ?? 0)}
            note="no transfer fee"
          />
          <StatTile
            label="In covered feed"
            value={formatInteger(count(summary, "in_covered_feed"))}
            note="current-season provider rows"
            indicator="unknown"
          />
          <StatTile
            label="Known top-flight abroad"
            value={formatInteger(count(summary, "top_flight_abroad"))}
            note="tier known only"
            indicator="unknown"
          />
          <StatTile
            label="At a rival now"
            value={formatInteger(count(summary, "at_rival_now"))}
            note="Celtic, Rangers, Dundee United"
          />
          <StatTile
            label="Rival spell"
            value={formatInteger(count(summary, "rival_spell"))}
            note="any post-Aberdeen spell"
          />
          <StatTile
            label="Young exits"
            value={formatInteger(count(summary, "young_exits"))}
            note="age 23 or younger"
            indicator="confidence"
          />
          <StatTile
            label="Early-career proxy"
            value={formatInteger(count(summary, "developed_here"))}
            note="not an academy register"
            indicator="confidence"
          />
        </div>
        <div className="grid two-col">
          <div className="card">
            <BucketBars title="Current or last-known leagues" buckets={currentLeagues} absolute />
            <BucketBars title="Current status" buckets={currentStatus} absolute />
          </div>
          <div className="card">
            <BucketBars title="Exit fee basis" buckets={feeBasis} absolute />
            <p className="fine-print">
              Fee basis comes from the transfer register. Undisclosed is never zero; a modelled
              range is not the club&apos;s internal valuation.
            </p>
          </div>
        </div>
      </ProfileSection>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Register</p>
            <h2>Every covered departure</h2>
          </div>
          <span className="badge badge-neutral">2019-20 onward</span>
        </div>
        <FormerPlayersBoard data={data} />
      </section>

      <ProfileSection
        eyebrow="Development pathway and exit outcomes"
        title="What happened next, without a verdict"
        badge={`${cohorts.all?.players ?? 0} players`}
        note={data.development_scorecard.note}
        indicator="confidence"
        contract="former.scorecard"
      >
        <div className="stat-row four">
          <StatTile
            label="Young exits"
            value={formatInteger(cohorts.young?.players ?? 0)}
            note={`with a fee: ${formatInteger(cohorts.young?.with_fee ?? 0)}`}
            indicator="confidence"
          />
          <StatTile
            label="Early-career exits"
            value={formatInteger(cohorts.developed_here?.players ?? 0)}
            note={`with a fee: ${formatInteger(cohorts.developed_here?.with_fee ?? 0)}`}
            indicator="confidence"
          />
          <StatTile
            label="Post-career minutes"
            value={formatInteger(cohorts.all?.post_career_minutes ?? 0)}
            note="covered league seasons"
            indicator="unknown"
          />
          <StatTile
            label="Faced Aberdeen"
            value={formatInteger(data.development_scorecard.vs_aberdeen.players_with_appearance ?? 0)}
            note={`${data.development_scorecard.vs_aberdeen.goals ?? 0} goals`}
          />
        </div>
        <div className="table-wrap">
          <table className="league-table compact">
            <caption className="fine-print">
              Descriptive cohorts by exit season. These are indicators, not proof that the model
              worked or that a sale was right.
            </caption>
            <thead>
              <tr>
                <th scope="col">Exit season</th>
                <th className="num" scope="col">Exits</th>
                <th className="num" scope="col">Young exits</th>
                <th className="num" scope="col">Early-career</th>
                <th className="num" scope="col">With a fee</th>
              </tr>
            </thead>
            <tbody>
              {data.development_scorecard.by_exit_season.map((row) => (
                <tr key={String(row.season)}>
                  <td>{String(row.season)}</td>
                  <td className="num">{formatInteger(Number(row.players ?? 0))}</td>
                  <td className="num">{formatInteger(Number(row.young_exits ?? 0))}</td>
                  <td className="num">{formatInteger(Number(row.developed_here ?? 0))}</td>
                  <td className="num">{formatInteger(Number(row.with_fee ?? 0))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print">
          The counterfactual is unobservable. A later career does not prove a sale was wrong; a
          fee does not prove the sale was sportingly costless. Early-career is a first-appearance
          proxy, not an academy classification.
        </p>
      </ProfileSection>

      <SellOnTable clauses={data.sell_on_watch.clauses} summary={data.sell_on_watch.summary} />

      <section className="section" data-contract="former.sale-chain">
        <div className="section-head">
          <div>
            <p className="eyebrow">Departure, after and sell-on</p>
            <h2>Sale chain</h2>
          </div>
          <span className="badge badge-neutral">Published link by link</span>
        </div>
        <p>
          Each former player&apos;s profile carries the chain from the Aberdeen
          departure through the post-Aberdeen record to any evidenced sell-on
          trigger and receipt. A missing fee, clause input or receipt stays
          unknown; the chain does not infer money or call a sale good or bad.
        </p>
        {data.sell_on_watch.clauses.length ? (
          <ul className="plain-list">
            {data.sell_on_watch.clauses.map((clause) => {
              const player = data.players.find(
                (row) => row.player_key === clause.player_key,
              );
              return (
                <li key={clause.clause_id}>
                  {player ? (
                    <Link
                      className="text-link"
                      href={`${player.href}#former-aberdeen`}
                    >
                      {clause.player_name}
                    </Link>
                  ) : (
                    clause.player_name
                  )}
                  <span className="muted">
                    {" "}
                    · {clause.sell_on_pct === null
                      ? "percentage undisclosed"
                      : `${clause.sell_on_pct}%`}{" "}
                    · basis {clause.basis} · trigger {clause.event_status} ·
                    receipt {clause.receipt.status.replaceAll("_", " ")}
                    {clause.receipt.missing_inputs.length
                      ? ` (missing: ${clause.receipt.missing_inputs.join(", ")})`
                      : ""}
                  </span>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="fine-print">No sell-on clause is recorded in this build.</p>
        )}
      </section>

      <FormerPlayerMentions forum={forum} rumours={rumours} />

      <ProfileSection
        eyebrow="Coverage and limits"
        title="What this record can and cannot say"
        badge={data.coverage.status}
        note={data.coverage.note}
        indicator="unknown"
        contract="former.coverage"
      >
        <p>
          The register covers confirmed business from {data.coverage.register_from}. Post-career
          league seasons are measured where API-Football covers them; a missing season is a gap,
          not zero. Some known players have a curated transfer identity but no API id, so they
          have no measured post-career record. Provider ratings are league-relative and are not
          compared across leagues. The page does not claim wages, add-ons, instalments, sell-on
          percentages or a good/bad-price verdict.
        </p>
        <p className="fine-print">
          Source rows: {data.sources.map((source) => source.name).join(", ")}. Last provider
          refresh:{" "}
          {data.coverage.post_career_updated_at
            ? formatDate(data.coverage.post_career_updated_at.slice(0, 10))
            : "not run"}.
          Sell-on receipts computed: {formatInteger(Number(summary.sell_on_computable ?? 0))}; known
          implied receipts:{" "}
          {summary.sell_on_implied_low_gbp === null || summary.sell_on_implied_low_gbp === undefined
            ? "unavailable"
            : formatGbp(Number(summary.sell_on_implied_low_gbp))}.
        </p>
        <p className="back-link">
          <Link href="/transfers/">← Confirmed transfer register</Link>
          {" · "}
          <Link href="/rumours/">Rumour mill</Link>
          {" · "}
          <Link href="/recruitment/">Off the pitch</Link>
          {" · "}
          <Link href="/squad/">Current squad</Link>
          {" · "}
          <Link href="/loans/">Loans</Link>
          {" · "}
          <Link href="/sources/">Sources</Link>
          {" · "}
          <Link href="/methodology/">Methodology</Link>
        </p>
      </ProfileSection>
    </ContractPage>
  );
}
