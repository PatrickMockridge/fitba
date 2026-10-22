import Link from "next/link";
import { EmptyState } from "@/components/EmptyState";
import { FixtureList } from "@/components/FixtureList";
import { FormGuide } from "@/components/FormGuide";
import { FormStrip } from "@/components/FormStrip";
import { KickoffNotice } from "@/components/KickoffNotice";
import { LegendDisclosure } from "@/components/LegendDisclosure";
import { MatchupRead } from "@/components/MatchupRead";
import { MetricStrip } from "@/components/MetricStrip";
import { PageHeader } from "@/components/PageHeader";
import { PredictedLineupPanel } from "@/components/PredictedLineupPanel";
import { StrengthComparison } from "@/components/StrengthComparison";
import { StyleMatchup } from "@/components/StyleMatchup";
import { TableFrame, Th } from "@/components/TableFrame";
import {
  formatDate,
  getMatchday,
  getThemes,
  type ClubFixture,
  type MatchdayDocument,
} from "@/lib/data";
import { plainText } from "@/lib/format";

export const metadata = { title: "Matchday · fitba" };

function fixtureList(data: MatchdayDocument): ClubFixture[] {
  return data.next_fixtures.slice(0, 2).map((fixture) => ({
    match_id: fixture.match_id,
    competition_id: fixture.competition_id,
    competition_name: fixture.competition_name,
    stage: fixture.stage,
    date: fixture.date,
    kickoff: fixture.kickoff,
    opponent_id: fixture.opponent_id,
    opponent_name: fixture.opponent_name,
    venue: fixture.venue === "H" ? "H" : "A",
    status: fixture.status,
  }));
}

function stateLabel(state: string) {
  if (state === "fresh") return "Snapshot fresh";
  if (state === "stale") return "Snapshot stale";
  if (state === "no_fixture") return "No fixture";
  return "Partial data";
}

export default function MatchdayPage() {
  const data = getMatchday();
  const themes = getThemes();
  if (!data) {
    return (
      <EmptyState
        title="No matchday snapshot published"
        body="The next-fixture projection appears after the next publish. Fixtures and league context are still available."
        action={
          <>
            <Link className="button" href="/fixtures/">
              Results &amp; fixtures
            </Link>
            <Link className="button button-ghost" href="/competitions/">
              Competitions
            </Link>
          </>
        }
      />
    );
  }

  if (data.state === "no_fixture" || !data.fixture) {
    return (
      <PageHeader
        eyebrow={`Matchday · Season ${data.season}`}
        title="No upcoming fixture"
        summary="There is no scheduled Aberdeen fixture in the local feed, so there is no matchday projection to show."
        actions={
          <>
            <Link className="button" href="/fixtures/">
              Results &amp; fixtures
            </Link>
            <Link className="button button-ghost" href="/squad/">
              Current squad
            </Link>
          </>
        }
      />
    );
  }

  const fixture = data.fixture;
  const opponent = data.teams.opponent;
  const aberdeen = data.teams.aberdeen;
  const next = fixtureList(data);
  const seasonTheme = (themes?.themes ?? []).find((theme) => theme.horizon === "season");
  const abdStrength = data.strength.aberdeen;
  const oppStrength = data.strength.opponent;
  const abdForm = data.form_guide.aberdeen;
  const abdLineup = data.predicted_lineups.aberdeen;

  return (
    <>
      <section className="matchday-head">
        <div className="matchday-head-top">
          <p className="eyebrow">
            {fixture.competition_name}
            {fixture.stage ? ` · ${fixture.stage}` : ""}
          </p>
          <p className="match-status">
            {stateLabel(data.state)} · Predicted, not team news
            {data.strength_comparison.cross_tier ? " · Cross-tier" : ""}
          </p>
        </div>
        <h1 className="versus">
          <span className="versus-side">
            <span className="versus-home">{fixture.home_team_name}</span>
            <span className="versus-note">Home</span>
          </span>
          <span className="versus-v">v</span>
          <span className="versus-side">
            <span className="versus-away">{fixture.away_team_name}</span>
            <span className="versus-note">Away</span>
          </span>
        </h1>
        <p className="match-meta">
          {formatDate(fixture.date)}
          {fixture.kickoff ? ` · ${fixture.kickoff}` : ""} ·{" "}
          {fixture.venue === "A"
            ? `Aberdeen away at ${fixture.home_team_name}`
            : `Aberdeen home to ${fixture.away_team_name}`}
        </p>
        <KickoffNotice date={fixture.date} kickoff={fixture.kickoff} />
        {data.state === "stale" ? (
          <p className="stale-banner">
            This snapshot is out of date. Check <Link href="/fixtures/">fixtures</Link>{" "}
            for the latest.
          </p>
        ) : null}
        {data.state === "unavailable" ? (
          <p className="stale-banner">
            The opponent snapshot is incomplete; the opponent XI and style read may be
            unavailable.
          </p>
        ) : null}
        {next.length ? (
          <div className="mini-block">
            <p className="eyebrow">Then</p>
            <FixtureList fixtures={next} empty="No further fixtures." />
          </div>
        ) : null}
      </section>

      <MetricStrip
        columns={4}
        items={[
          {
            label: aberdeen?.name ?? "Aberdeen",
            value: abdStrength?.position ? `${abdStrength.position}th` : "—",
            note: abdStrength?.points != null ? `${abdStrength.points} pts` : "League",
          },
          {
            label: opponent?.name ?? fixture.opponent_name,
            value: oppStrength?.position ? `${oppStrength.position}th` : "—",
            note: oppStrength?.ppg != null ? `${oppStrength.ppg} PPG` : "League",
          },
          {
            label: "Form",
            value: abdForm?.form ? <FormStrip form={abdForm.form} /> : "—",
            note: "Last five",
          },
          {
            label: "Predicted shape",
            value: abdLineup?.formation ?? "—",
            note: abdLineup?.team_confidence ? `${abdLineup.team_confidence} confidence` : "Not team news",
          },
        ]}
      />

      {data.matchup_read ? <MatchupRead read={data.matchup_read} /> : null}

      <section className="section">
        <div className="section-head">
          <h2>Who starts?</h2>
          <span className="muted">Predicted, not team news</span>
        </div>
        <div className="grid two-col lineup-grid">
          <PredictedLineupPanel
            teamName={aberdeen?.name ?? "Aberdeen"}
            block={data.predicted_lineups.aberdeen ?? null}
            isAberdeen
          />
          <PredictedLineupPanel
            teamName={opponent?.name ?? fixture.opponent_name}
            block={data.predicted_lineups.opponent ?? null}
          />
        </div>
      </section>

      {data.form_guide.aberdeen && data.form_guide.opponent ? (
        <FormGuide
          aberdeenName={aberdeen?.name ?? "Aberdeen"}
          opponentName={opponent?.name ?? fixture.opponent_name}
          aberdeen={data.form_guide.aberdeen}
          opponent={data.form_guide.opponent}
        />
      ) : null}

      {data.styles.aberdeen && data.styles.opponent ? (
        <StyleMatchup
          aberdeenName={aberdeen?.name ?? "Aberdeen"}
          opponentName={opponent?.name ?? fixture.opponent_name}
          aberdeen={data.styles.aberdeen}
          opponent={data.styles.opponent}
        />
      ) : null}

      {data.strength.aberdeen && data.strength.opponent ? (
        <StrengthComparison
          aberdeenName={aberdeen?.name ?? "Aberdeen"}
          opponentName={opponent?.name ?? fixture.opponent_name}
          aberdeen={data.strength.aberdeen}
          opponent={data.strength.opponent}
          comparison={data.strength_comparison}
        />
      ) : null}

      {seasonTheme ? (
        <section className="section">
          <div className="section-head">
            <h2>What is the bigger picture?</h2>
            <Link className="text-link" href="/themes/">
              Themes →
            </Link>
          </div>
          <p className="page-summary">
            {plainText(seasonTheme.headline ?? seasonTheme.title)}
          </p>
        </section>
      ) : null}

      {data.head_to_head.length ? (
        <section className="section">
          <div className="section-head">
            <h2>Recent meetings</h2>
            <span className="muted">League meetings</span>
          </div>
          <TableFrame label="Recent meetings" caption="Recent league meetings between the two teams">
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>Match</Th>
                <Th className="num">Score</Th>
                <Th>Aberdeen</Th>
              </tr>
            </thead>
            <tbody>
              {data.head_to_head.slice(0, 3).map((meeting) => (
                <tr key={`${meeting.date}-${meeting.home_team_name}`}>
                  <td>{formatDate(meeting.date)}</td>
                  <td>
                    {meeting.home_team_name} v {meeting.away_team_name}
                  </td>
                  <td className="num">
                    {meeting.home_goals ?? "—"}–{meeting.away_goals ?? "—"}
                  </td>
                  <td>{meeting.result ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </TableFrame>
        </section>
      ) : null}

      <LegendDisclosure title="How this projection is built">
        <p>
          Form is league-only. Style uses shots, shot share, shots on target and
          goals; possession is unknown and is not used. Strength percentiles are
          within the same league. Predicted XIs use recent starts, minutes,
          formation and position fit.
        </p>
        <p>{data.coverage.note}</p>
        <p>
          <Link href="/methodology/">Method</Link> ·{" "}
          <Link href="/sources/">Sources</Link> ·{" "}
          <Link href="/squad/">Squad</Link> ·{" "}
          <Link href="/fixtures/">All fixtures</Link>
        </p>
      </LegendDisclosure>
    </>
  );
}
