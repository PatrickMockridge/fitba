import Link from "next/link";
import { notFound } from "next/navigation";
import { ContractPage } from "@/components/ContractPage";
import { MatchCoverage } from "@/components/MatchCoverage";
import { MatchHeader } from "@/components/MatchHeader";
import { MatchPlayerTable } from "@/components/MatchPlayerTable";
import { MatchScoreboard } from "@/components/MatchScoreboard";
import { MatchStatsTable } from "@/components/MatchStatsTable";
import { MatchSummary } from "@/components/MatchSummary";
import { MatchTimeline } from "@/components/MatchTimeline";
import { ObservedLineup } from "@/components/ObservedLineup";
import { getFixture, getFixtureIndex } from "@/lib/data";
import { formatDate } from "@/lib/format";

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
      <section
        className="card"
        data-contract="match.xg"
        data-team-split="aberdeen-opponent"
      >
        <div className="section-head">
          <div>
            <p className="eyebrow">Expected goals</p>
            <h2>fxG and provider xG</h2>
          </div>
          <span className="badge badge-neutral">experimental</span>
        </div>
        {data.xg.available && data.xg.gate_passed === false ? (
          <p className="fine-print" data-contract="match.xg.gate">
            <span className="badge badge-warn">fxG gate failed</span>{" "}
            {data.xg.gate_note ?? "The model is descriptive, not decision-grade."}{" "}
            <Link className="text-link" href={data.xg.evaluation_href ?? "/analysis/xg/"}>
              Model and gate →
            </Link>
          </p>
        ) : null}
        {data.xg.available && data.xg.gate_passed === true ? (
          <p className="fine-print" data-contract="match.xg.gate">
            <span className="badge badge-ok">fxG gate passed</span>{" "}
            <Link className="text-link" href={data.xg.evaluation_href ?? "/analysis/xg/"}>
              Model and gate →
            </Link>
          </p>
        ) : null}
        {data.xg.available && data.xg.home && data.xg.away ? (
          <div className="match-xg-grid">
            <div
              className="match-xg-side"
              data-team={aberdeenIsHome ? "aberdeen" : "opponent"}
            >
              <p className="eyebrow">{home}</p>
              <p className="stat-value">{data.xg.home.value ?? "—"}</p>
              <p className="fine-print">
                fxG interval {data.xg.home.low ?? "—"}–{data.xg.home.high ?? "—"}
              </p>
              <p className="fine-print">
                Provider xG {data.xg.home.provider ?? "unavailable"}
              </p>
            </div>
            <div
              className="match-xg-side"
              data-team={aberdeenIsHome ? "opponent" : "aberdeen"}
            >
              <p className="eyebrow">{away}</p>
              <p className="stat-value">{data.xg.away.value ?? "—"}</p>
              <p className="fine-print">
                fxG interval {data.xg.away.low ?? "—"}–{data.xg.away.high ?? "—"}
              </p>
              <p className="fine-print">
                Provider xG {data.xg.away.provider ?? "unavailable"}
              </p>
            </div>
          </div>
        ) : (
          <p className="fine-print">
            fxG is unavailable for this fixture because shots on target are not
            in the record. It is not shown as zero.
          </p>
        )}
        <p className="fine-print">
          {data.xg.note ?? "fxG is a shot-on-target model, not provider xG."}
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
            Match record →
          </Link>
        </p>
      </section>
    </ContractPage>
  );
}
