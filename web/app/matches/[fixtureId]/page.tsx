import Link from "next/link";
import { notFound } from "next/navigation";
import { ContractPage } from "@/components/ContractPage";
import { MatchCoverage } from "@/components/MatchCoverage";
import { MatchHeader } from "@/components/MatchHeader";
import { MatchPerformance } from "@/components/MatchPerformance";
import { MatchPlayerTable } from "@/components/MatchPlayerTable";
import { MatchScoreboard } from "@/components/MatchScoreboard";
import { MatchStatsTable } from "@/components/MatchStatsTable";
import { MatchSummary } from "@/components/MatchSummary";
import { MatchTimeline } from "@/components/MatchTimeline";
import { ObservedLineup } from "@/components/ObservedLineup";
import { getFixture, getFixtureIndex } from "@/lib/data";
import { formatDate, formatDecimal, formatInteger, formatSigned } from "@/lib/format";

export const dynamicParams = false;

export function generateStaticParams() {
  const index = getFixtureIndex();
  return [...(index?.fixtures ?? []), ...(index?.aliases ?? [])].map((row) => ({
    fixtureId: String(row.fixture_id),
  }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ fixtureId: string }>;
}) {
  const { fixtureId } = await params;
  const data = getFixture(fixtureId);
  if (!data) return { title: "Match · fitba" };
  const f = data.fixture;
  const duplicate = Boolean(f.duplicate_of);
  const title = `${f.home_team_name} ${f.home_goals ?? "–"}–${f.away_goals ?? "–"} ${f.away_team_name} · ${formatDate(f.date)}${duplicate ? ` (duplicate record ${fixtureId})` : ""} · fitba`;
  const description = `${f.competition_name}, ${formatDate(f.date)}. The measured match record, scoreboard, events and coverage.`;
  return {
    title,
    description,
    alternates: { canonical: f.duplicate_of ?? `/matches/${fixtureId}/` },
    openGraph: { title, description, type: "article" },
    twitter: { card: "summary", title, description },
    robots: f.duplicate_of ? { index: false, follow: true } : undefined,
  };
}

export default async function MatchPage({
  params,
}: {
  params: Promise<{ fixtureId: string }>;
}) {
  const { fixtureId } = await params;
  const data = getFixture(fixtureId);
  if (!data) notFound();
  const f = data.fixture;
  const home = f.home_team_name;
  const away = f.away_team_name;
  const aberdeenIsHome = f.home_team_id === "sco:aberdeen";
  return (
    <ContractPage surface="match">
      {f.duplicate_of ? (
        <p className="stale-banner" data-contract="match.duplicate">
          This is a duplicate fixture record. The canonical match is{" "}
          <Link className="text-link" href={f.duplicate_of}>
            here
          </Link>
          ; counts and navigation use the canonical record.
        </p>
      ) : null}
      <MatchHeader fixture={data} />
      <MatchScoreboard fixture={data} />
      <MatchSummary summary={data.summary} />
      <MatchStatsTable
        stats={data.stats}
        home={home}
        away={away}
        aberdeenIsHome={aberdeenIsHome}
      />
      <MatchPerformance
        performance={data.performance}
        home={home}
        away={away}
        aberdeenIsHome={aberdeenIsHome}
      />
      <section
        className="card"
        data-contract="match.xg"
        data-team-split="aberdeen-opponent"
      >
        <div className="section-head">
          <div>
            <p className="eyebrow">Expected goals</p>
            <h2>fxG, its ranges and provider xG</h2>
          </div>
          <span className="badge badge-neutral">experimental</span>
        </div>
        {data.xg.available && data.xg.gate_passed === false ? (
          <p className="fine-print" data-contract="match.xg.gate">
            <span className="badge badge-warn">fxG calibration failed</span>{" "}
            {data.xg.gate_note ?? "The model is descriptive, not decision-grade."}{" "}
            <Link className="text-link" href={data.xg.evaluation_href ?? "/analysis/xg/"}>
              Model and calibration →
            </Link>
          </p>
        ) : null}
        {data.xg.available && data.xg.gate_passed === true ? (
          <p className="fine-print" data-contract="match.xg.gate">
            <span className="badge badge-ok">fxG calibration passed · in-season</span>{" "}
            <Link className="text-link" href={data.xg.evaluation_href ?? "/analysis/xg/"}>
              Model and calibration →
            </Link>
          </p>
        ) : null}
        {data.xg.available && data.xg.home && data.xg.away ? (
          <div className="match-xg-grid">
            {[data.xg.home, data.xg.away].map((side, index) => {
              const team = index === 0 ? home : away;
              const isAberdeen = index === 0 ? aberdeenIsHome : !aberdeenIsHome;
              const interval = (low: number | null, high: number | null) =>
                low === null || high === null
                  ? "unavailable"
                  : `${formatDecimal(low, 2)}–${formatDecimal(high, 2)}`;
              const goalInterval = (low: number | null, high: number | null) =>
                low === null || high === null
                  ? "unavailable"
                  : `${formatInteger(low)}–${formatInteger(high)}`;
              const position =
                side.goals_position === "above"
                  ? "above the 80% goals range"
                  : side.goals_position === "below"
                    ? "below the 80% goals range"
                    : side.goals_position === "within"
                      ? "within the 80% goals range"
                      : "position unavailable";
              return (
                <div
                  key={team}
                  className="match-xg-side"
                  data-team={isAberdeen ? "aberdeen" : "opponent"}
                >
                  <p className="eyebrow">{team}</p>
                  <p className="stat-value">
                    {side.value === null ? "—" : formatDecimal(side.value, 2)}
                  </p>
                  <p className="fine-print" data-contract="match.xg.model-range">
                    <strong>80% model range</strong> {interval(side.low, side.high)}
                  </p>
                  <p className="fine-print" data-contract="match.xg.goals-range">
                    <strong>80% goals range</strong>{" "}
                    {goalInterval(side.goals_low, side.goals_high)}
                  </p>
                  <p className="fine-print" data-contract="match.xg.provider">
                    <strong>Provider xG</strong>{" "}
                    {side.provider === null
                      ? "unavailable"
                      : formatDecimal(side.provider, 2)}
                    {side.provider_source
                      ? ` · ${side.provider_source === "api_football" ? "API-Football" : "football-data.co.uk"}`
                      : ""}
                  </p>
                  <p className="fine-print" data-contract="match.xg.overperformance">
                    <strong>Goals − fxG</strong>{" "}
                    {side.goals_minus === null ? "—" : formatSigned(side.goals_minus)} ·{" "}
                    {position}
                  </p>
                  <p className="fine-print" data-contract="match.xg.penalties">
                    <strong>Penalties</strong>{" "}
                    {side.penalties_known === false || side.penalties === null
                      ? "not available"
                      : `${formatInteger(side.penalties)} · ${
                          side.penalty_xg === null
                            ? "—"
                            : formatDecimal(side.penalty_xg, 2)
                        } xG`}
                  </p>
                  <p className="fine-print" data-contract="match.xg.shot-profile">
                    <strong>xG per shot</strong>{" "}
                    {side.xg_per_shot === null
                      ? "—"
                      : formatDecimal(side.xg_per_shot, 3)}{" "}
                    · {formatInteger(side.shot_profile?.shots ?? 0)} shots ·{" "}
                    {formatInteger(side.shot_profile?.shots_on_target ?? 0)} on target ·{" "}
                    {formatInteger(side.shot_profile?.shots_insidebox ?? 0)} inside box
                  </p>
                  <p className="fine-print">
                    Basis: {side.basis ?? "unavailable"}. The model range is
                    uncertainty in the estimate; the goals range is the spread of
                    goals from the same chances. Neither is a result prediction.
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="fine-print" data-contract="match.xg.unavailable">
            fxG is unavailable for this fixture because shots on target are not
            in the record. It is not shown as zero.
          </p>
        )}
        <p className="fine-print">
          {data.xg.note ??
            "fxG is a team-match estimate, not provider xG and not a shot-level model."}{" "}
          Own goals and shootouts are outside the shot model. Provider xG is a
          different model and is never blended into fxG.
        </p>
      </section>

      <MatchTimeline timeline={data.timeline} aberdeenIsHome={aberdeenIsHome} />
      <div className="match-lineups-grid" data-team-split="aberdeen-opponent">
        <ObservedLineup
          lineup={data.lineups.home}
          teamName={home}
          isAberdeen={aberdeenIsHome}
        />
        <ObservedLineup
          lineup={data.lineups.away}
          teamName={away}
          isAberdeen={!aberdeenIsHome}
        />
      </div>
      <MatchPlayerTable players={data.player_stats} />
      <MatchCoverage coverage={data.coverage} />
      <section className="card" data-contract="match.links">
        <div className="section-head">
          <div>
            <p className="eyebrow">Record</p>
            <h2>Before and after</h2>
          </div>
        </div>
        <div className="match-form-grid">
          <div>
            <h3>Before</h3>
            <ul className="plain-list">
              {data.form.before.map((row) => (
                <li key={row.fixture_id}>
                  <Link href={row.href}>
                    {formatDate(row.date)} · {row.opponent_name} ·{" "}
                    {row.goals_for}–{row.goals_against}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>After</h3>
            <ul className="plain-list">
              {data.form.after.map((row) => (
                <li key={row.fixture_id}>
                  <Link href={row.href}>
                    {formatDate(row.date)} · {row.opponent_name} ·{" "}
                    {row.goals_for}–{row.goals_against}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <p className="fine-print">
          <Link className="text-link" href={data.links.season ?? "/history/"}>
            {f.season} season →
          </Link>{" "}
          <Link className="text-link" href="/matches/">
            Results and fixtures →
          </Link>
        </p>
      </section>
    </ContractPage>
  );
}
