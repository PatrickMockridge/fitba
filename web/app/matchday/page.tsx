import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { FixtureList } from "@/components/FixtureList";
import { FormGuide } from "@/components/FormGuide";
import { KickoffNotice } from "@/components/KickoffNotice";
import { MatchupRead } from "@/components/MatchupRead";
import { PredictedLineupPanel } from "@/components/PredictedLineupPanel";
import { StrengthComparison } from "@/components/StrengthComparison";
import { StyleMatchup } from "@/components/StyleMatchup";
import { ThemeCard } from "@/components/ThemeCard";
import {
  formatDate,
  getMatchday,
  getThemes,
  type ClubFixture,
  type MatchdayDocument,
} from "@/lib/data";

export const metadata = { title: "Matchday · fitba" };

function snapshotValue(
  data: MatchdayDocument,
  key: string,
): string | number | null {
  const value = (data.coverage.snapshot ?? {})[key];
  return typeof value === "string" || typeof value === "number" ? value : null;
}

function stateBadge(state: string) {
  if (state === "fresh") {
    return <span className="badge badge-ok">Snapshot fresh</span>;
  }
  if (state === "stale") {
    return <span className="badge badge-warn">Stale snapshot</span>;
  }
  if (state === "no_fixture") {
    return <span className="badge badge-neutral">No fixture</span>;
  }
  return <span className="badge badge-warn">Partial data</span>;
}

function fixtureList(data: MatchdayDocument): ClubFixture[] {
  return data.next_fixtures.map((fixture) => ({
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

export default function MatchdayPage() {
  const data = getMatchday();
  const themes = getThemes();
  if (!data) {
    return (
      <ContractPage surface="matchday" state="empty">
        <section className="empty-state" data-contract="matchday.empty">
          <h1>No matchday snapshot published</h1>
          <p>
            Run <code>uv run fitba matchday --refresh</code> and then{" "}
            <code>uv run fitba publish</code>.
          </p>
          <p>
            The page needs a local opponent snapshot. Form and league context can
            still be viewed on <Link href="/fixtures/">fixtures</Link> and{" "}
            <Link href="/competitions/">competitions</Link>.
          </p>
        </section>
      </ContractPage>
    );
  }

  if (data.state === "no_fixture" || !data.fixture) {
    return (
      <ContractPage surface="matchday" state="no-fixture">
        <section className="page-head" data-contract="matchday.no-fixture">
          <p className="eyebrow">Matchday · Season {data.season}</p>
          <h1>No upcoming fixture</h1>
          <p className="lede">
            There is no scheduled Aberdeen fixture in the local feed, so there
            is no matchday projection to show.
          </p>
          <div className="hero-actions">
            <Link className="button" href="/fixtures/">
              Results &amp; fixtures
            </Link>
            <Link className="button button-ghost" href="/competitions/">
              Competitions
            </Link>
            <Link className="button button-ghost" href="/squad/">
              Current squad
            </Link>
          </div>
          {data.stale_reason ? (
            <p className="fine-print">State: {data.stale_reason.replaceAll("_", " ")}.</p>
          ) : null}
        </section>
      </ContractPage>
    );
  }

  const fixture = data.fixture;
  const opponent = data.teams.opponent;
  const aberdeen = data.teams.aberdeen;
  const snapshotAt = snapshotValue(data, "generated_at");
  const age = snapshotValue(data, "age_hours");
  const lineupStatus = data.coverage.lineups ?? {};
  const next = fixtureList(data);
  const seasonThemes = (themes?.themes ?? []).filter(
    (theme) => theme.horizon === "season",
  );
  const missionTheme = (themes?.themes ?? []).find(
    (theme) => theme.horizon === "mission",
  );

  return (
    <ContractPage surface="matchday">
      <section className="matchday-head" data-contract="matchday.fixture">
        <div className="matchday-head-top">
          <p className="eyebrow">
            {fixture.competition_name}
            {fixture.stage ? ` · ${fixture.stage}` : ""}
          </p>
          <div className="badge-row">
            {stateBadge(data.state)}
            <span className="badge badge-neutral">Predicted, not team news</span>
            {data.strength_comparison.cross_tier ? (
              <span className="badge badge-warn">Cross-tier</span>
            ) : null}
          </div>
        </div>
        <h1
          className="versus"
          aria-label={`${fixture.home_team_name} v ${fixture.away_team_name}`}
        >
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
            This snapshot is out of date
            {snapshotAt ? ` (${formatDate(String(snapshotAt).slice(0, 10))})` : ""}.
            Check <Link href="/fixtures/">fixtures</Link> for the latest.
          </p>
        ) : null}
        {data.state === "unavailable" ? (
          <p className="stale-banner">
            The opponent snapshot is incomplete. Form and league context are
            shown, but the opponent XI and style read may be unavailable.
          </p>
        ) : null}
        <div className="matchday-meta-row">
          <span className="fine-print">
            {snapshotAt
              ? `Opponent snapshot ${formatDate(String(snapshotAt).slice(0, 10))}`
              : "No opponent snapshot"}
            {age !== null ? ` · ${age}h old` : ""}
          </span>
          <span className="fine-print">
            Aberdeen XI: {lineupStatus.aberdeen ?? "unknown"} · Opponent XI:{" "}
            {lineupStatus.opponent ?? "unknown"}
          </span>
        </div>
        {next.length ? (
          <div className="mini-block">
            <p className="eyebrow">Then</p>
            <FixtureList fixtures={next} empty="No further fixtures." />
          </div>
        ) : null}
      </section>

      {data.matchup_read ? (
        <MatchupRead
          read={data.matchup_read}
          contract="matchday.matchup-read"
        />
      ) : null}

      <section className="section" data-contract="matchday.predicted-xis">
        <div className="section-head">
          <div>
            <p className="eyebrow">Projected line-ups</p>
            <h2>Predicted XIs</h2>
          </div>
          <span className="badge badge-neutral">Not official team news</span>
        </div>
        <div className="grid two-col lineup-grid">
          <PredictedLineupPanel
            teamName={aberdeen?.name ?? "Aberdeen"}
            block={data.predicted_lineups.aberdeen ?? null}
            isAberdeen
            contract="matchday.lineup"
          />
          <PredictedLineupPanel
            teamName={opponent?.name ?? fixture.opponent_name}
            block={data.predicted_lineups.opponent ?? null}
            contract="matchday.lineup"
          />
        </div>
      </section>

      {data.form_guide.aberdeen && data.form_guide.opponent ? (
        <FormGuide
          aberdeenName={aberdeen?.name ?? "Aberdeen"}
          opponentName={opponent?.name ?? fixture.opponent_name}
          aberdeen={data.form_guide.aberdeen}
          opponent={data.form_guide.opponent}
          contract="matchday.form-guide"
        />
      ) : null}

      {data.styles.aberdeen && data.styles.opponent ? (
        <StyleMatchup
          aberdeenName={aberdeen?.name ?? "Aberdeen"}
          opponentName={opponent?.name ?? fixture.opponent_name}
          aberdeen={data.styles.aberdeen}
          opponent={data.styles.opponent}
          venueLabel="Home / away"
          contract="matchday.style"
        />
      ) : null}

      {data.strength.aberdeen && data.strength.opponent ? (
        <StrengthComparison
          aberdeenName={aberdeen?.name ?? "Aberdeen"}
          opponentName={opponent?.name ?? fixture.opponent_name}
          aberdeen={data.strength.aberdeen}
          opponent={data.strength.opponent}
          comparison={data.strength_comparison}
          contract="matchday.strength"
        />
      ) : null}

      {themes && (seasonThemes.length || missionTheme) ? (
        <section className="section" data-contract="matchday.themes">
          <div className="section-head">
            <div>
              <p className="eyebrow">The bigger picture · 80% season, 20% mission</p>
              <h2>What backs this matchday</h2>
            </div>
            <Link className="text-link" href="/themes/">
              Full evidence →
            </Link>
          </div>
          <div className="theme-strip">
            {seasonThemes.map((theme) => (
              <ThemeCard
                key={theme.theme_id}
                theme={theme}
                compact
                contract="matchday.theme"
              />
            ))}
          </div>
          {missionTheme ? (
            <ThemeCard
              theme={missionTheme}
              compact
              contract="matchday.theme"
            />
          ) : null}
          <p className="fine-print">
            Four current-season themes and one Cormack-era mission theme.
            Provider ratings are league-only and never an individual verdict;
            read the{" "}
            <Link className="text-link" href="/themes/">
              full evidence and caveats
            </Link>
            .
          </p>
        </section>
      ) : null}

      {data.head_to_head.length ? (
        <section className="card" data-contract="matchday.head-to-head">
          <div className="section-head">
            <div>
              <p className="eyebrow">Context, not a prediction</p>
              <h2>Recent meetings</h2>
            </div>
            <span className="badge badge-neutral">League meetings</span>
          </div>
          <div className="table-wrap">
            <table className="league-table compact">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Match</th>
                  <th className="num">Score</th>
                  <th>Aberdeen</th>
                </tr>
              </thead>
              <tbody>
                {data.head_to_head.map((meeting) => (
                  <tr key={`${meeting.date}-${meeting.home_team_name}`}>
                    <td>{formatDate(meeting.date)}</td>
                    <td>
                      {meeting.home_team_name} v {meeting.away_team_name}
                    </td>
                    <td className="num">
                      {meeting.home_goals ?? "—"}–{meeting.away_goals ?? "—"}
                    </td>
                    <td>
                      <span
                        className={`result-dot result-${(meeting.result ?? "").toLowerCase()}`}
                      >
                        {meeting.result ?? "?"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="card coverage-card" data-contract="matchday.coverage">
        <div className="card-head">
          <div>
            <p className="eyebrow">How to read this page</p>
            <h2>Coverage and limits</h2>
          </div>
          <span className="badge badge-neutral">
            {data.coverage.state ?? data.state}
          </span>
        </div>
        <ul className="plain-list">
          <li>
            <strong>Form</strong> is league-only and uses the last five results;
            home and away splits use every league match.
          </li>
          <li>
            <strong>Style</strong> is measured from shots, shots on target,
            goals and corners. Possession is unknown and is not used. It is not
            xG and not a tactical model.
          </li>
          <li>
            <strong>Predicted XIs</strong> come from recent starts, minutes,
            formation and position fit. They are not team news.
          </li>
          <li>
            <strong>Strength</strong> percentiles are within the same league.
            Cross-tier comparisons show raw values only.
          </li>
        </ul>
        <p className="fine-print">{data.coverage.note}</p>
        <p className="fine-print" data-contract-indicator="source">
          Snapshot: {snapshotAt ? String(snapshotAt) : "none"} ·{" "}
          {typeof data.coverage.snapshot?.fixtures === "number"
            ? `${data.coverage.snapshot.fixtures} opponent fixtures`
            : "no opponent fixtures"}{" "}
          · {typeof data.coverage.snapshot?.fixtures_with_lineups === "number"
            ? `${data.coverage.snapshot.fixtures_with_lineups} with lineups`
            : "no lineup count"}
          . <Link className="text-link" href="/methodology/">Method →</Link>{" "}
          <Link className="text-link" href="/sources/">Sources →</Link>
        </p>
        <p className="back-link">
          <Link href="/fixtures/">All fixtures</Link>
          {" · "}
          <Link href="/competitions/">Competitions</Link>
          {" · "}
          <Link href="/squad/">Squad</Link>
          {" · "}
          <Link href="/history/">The Cormack era</Link>
          {" · "}
          <Link href="/transfers/">Transfers</Link>
        </p>
      </section>

      <p className="fine-print">{data.notes}</p>
    </ContractPage>
  );
}
