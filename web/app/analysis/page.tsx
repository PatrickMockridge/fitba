import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { TableFrame } from "@/components/TableFrame";
import {
  formatDate,
  formatDecimal,
  formatInteger,
  formatPercentValue,
  formatSigned,
} from "@/lib/format";
import { getAnalysisSummary } from "@/lib/data";
import type {
  AnalysisAim,
  AnalysisAvailabilityReview,
  AnalysisFixture,
  AnalysisInference,
  AnalysisLens,
  AnalysisLeagueRankings,
  AnalysisOfficial,
  AnalysisReviewRow,
  AnalysisSelection,
  AnalysisSuspension,
} from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/analysis/" },
  title: "Season overview · fitba",
  description:
    "Aberdeen's season at a glance: league rankings for xG, possession and goals, next fixtures, availability, aims, squad decisions and the route to the evidence.",
};

function ordinal(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const suffix = value % 10 === 1 && value % 100 !== 11 ? "st" : value % 10 === 2 && value % 100 !== 12 ? "nd" : value % 10 === 3 && value % 100 !== 13 ? "rd" : "th";
  return `${value}${suffix}`;
}

function venueLabel(value: string, neutral: boolean): string {
  if (neutral) return "Neutral";
  if (value === "H") return "Home";
  if (value === "A") return "Away";
  return "Neutral";
}

function FixtureTable({ rows }: { rows: AnalysisFixture[] }) {
  if (!rows.length) {
    return <p className="fine-print">No scheduled fixture is published for this season.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="league-table compact">
        <caption className="fine-print">
          Next three competitive fixtures. Kickoff is Europe/London; provisional times are marked.
        </caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Competition</th>
            <th scope="col">Opponent</th>
            <th scope="col">Venue</th>
            <th scope="col">Kickoff</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row.fixture_id ?? `${row.date}-${row.competition_id}`)}>
              <td>{formatDate(row.date)}</td>
              <td>{row.competition_name}</td>
              <td>
                {row.opponent_name}
                {row.stage ? <span className="badge badge-neutral"> {row.stage}</span> : null}
              </td>
              <td>{venueLabel(row.venue, row.neutral)}</td>
              <td>
                {row.kickoff ?? "TBC"}
                {row.kickoff_status === "provisional" ? " (prov.)" : ""}
              </td>
              <td>{row.conflict_review ? "Conflict — review" : "Scheduled"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OfficialTable({ rows }: { rows: AnalysisOfficial[] }) {
  if (!rows.length) {
    return <p className="fine-print">No verified official team-news entry is published.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="league-table compact">
        <caption className="fine-print">
          Official AFC team news only. Available means a verified ledger entry, not fit.
        </caption>
        <thead>
          <tr>
            <th scope="col">Player</th>
            <th scope="col">Status</th>
            <th scope="col">Reason</th>
            <th scope="col">Confidence</th>
            <th scope="col">Verified</th>
            <th scope="col">Source</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.player_id}>
              <td>
                <Link href={`/players/${row.player_id}/`}>{row.player_name ?? row.player_id}</Link>
              </td>
              <td>
                {row.status}
                {row.review_required ? (
                  <span className="badge badge-warn" title={row.review_reason ?? "Needs review"}>
                    {" "}
                    review
                  </span>
                ) : null}
              </td>
              <td>{row.reason ?? "—"}</td>
              <td>{row.confidence ?? "unknown"}</td>
              <td>{row.verified_at ? formatDate(row.verified_at) : "—"}</td>
              <td>
                {row.source_url ? (
                  <a href={row.source_url} target="_blank" rel="noreferrer">
                    {row.source_id ?? "source"}
                  </a>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function reviewEvidence(row: AnalysisReviewRow): string {
  const contradiction = row.contradicted_by;
  if (contradiction) {
    const parts = [
      contradiction.squad_status
        ? String(contradiction.squad_status).replaceAll("_", " ")
        : null,
      contradiction.date ? formatDate(String(contradiction.date)) : null,
      contradiction.minutes !== undefined && contradiction.minutes !== null
        ? `${contradiction.minutes} min`
        : null,
      contradiction.opponent_name ? `v ${contradiction.opponent_name}` : null,
    ].filter(Boolean);
    if (parts.length) return parts.join(" · ");
  }
  const suspension = row.suspension;
  if (suspension) {
    if (suspension.state === "served") {
      const date = suspension.served_date ? formatDate(String(suspension.served_date)) : null;
      const matches = suspension.ban_matches
        ? `${suspension.ban_matches} match${Number(suspension.ban_matches) === 1 ? "" : "es"}`
        : null;
      return ["served", date, matches].filter(Boolean).join(" · ");
    }
    if (suspension.state === "not_applied") return "Not applied";
    if (suspension.state) return String(suspension.state).replaceAll("_", " ");
  }
  if (row.status_age_days !== null && row.status_age_days !== undefined) {
    return `${formatInteger(row.status_age_days)} days old`;
  }
  return "—";
}

function ReviewTable({ review }: { review: AnalysisAvailabilityReview }) {
  const ledger = review.ledger ?? {};
  return (
    <div className="table-wrap">
      <table className="league-table compact">
        <caption className="fine-print">
          Contradicted or aging team-news claims. A contradicted claim is unknown, not
          fit; an aging claim keeps its recorded status with a review flag. The
          recorded claim, source and evidence stay visible.{" "}
          {ledger.ledger_updated_at
            ? `Ledger updated ${formatDate(String(ledger.ledger_updated_at))}`
            : null}
          {ledger.latest_news_date
            ? ` · latest AFC news ${formatDate(String(ledger.latest_news_date))}`
            : null}
          .
        </caption>
        <thead>
          <tr>
            <th scope="col">Player</th>
            <th scope="col">Published status</th>
            <th scope="col">Recorded status</th>
            <th scope="col">Verified</th>
            <th scope="col">Source</th>
            <th scope="col">Evidence</th>
            <th scope="col">Review reason</th>
          </tr>
        </thead>
        <tbody>
          {review.rows.length === 0 ? (
            <tr>
              <td>—</td>
              <td>—</td>
              <td>—</td>
              <td>—</td>
              <td>—</td>
              <td>—</td>
              <td>—</td>
            </tr>
          ) : (
            review.rows.map((row) => (
              <tr key={row.player_id}>
                <td>
                  <Link href={`/players/${row.player_id}/`}>
                    {row.player_name ?? row.player_id}
                  </Link>
                </td>
                <td>{row.status}</td>
                <td>{row.original_status ?? "—"}</td>
                <td>{row.verified_at ? formatDate(row.verified_at) : "—"}</td>
                <td>
                  {row.source_url ? (
                    <a href={row.source_url} target="_blank" rel="noreferrer">
                      {row.source_id ?? "source"}
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
                <td>{reviewEvidence(row)}</td>
                <td>{row.review_reason?.replaceAll("_", " ") ?? "—"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function SuspensionRows({ rows }: { rows: AnalysisSuspension[] }) {
  if (!rows.length) return <p className="fine-print">No suspension watch at current coverage.</p>;
  return (
    <ul className="plain-list">
      {rows.map((row) => (
        <li key={`${row.player_id}-${row.competition_id}`}>
          <Link href={`/players/${row.player_id}/`}>{row.player_name ?? row.player_id}</Link>{" "}
          <span className="muted">
            · {row.competition_name} ·{" "}
            {row.reds
              ? `${row.reds} red${row.red_type ? ` (${row.red_type.replaceAll("_", " ")})` : ""}`
              : `${row.cautions}/${row.threshold ?? "?"} cautions`}
          </span>{" "}
          <span
            className={
              row.status === "served" || row.status === "resolved"
                ? "badge badge-ok"
                : "badge badge-warn"
            }
          >
            {row.status.replaceAll("_", " ")}
          </span>
          {row.status === "served" && row.served_date ? (
            <span className="muted">
              {" "}
              · served {formatDate(row.served_date)}
              {row.ban_matches
                ? ` · ${row.ban_matches} match${row.ban_matches === 1 ? "" : "es"}`
                : ""}
            </span>
          ) : null}
          {row.next_fixture ? (
            <span className="muted">
              {" "}
              · next: {row.next_fixture.opponent_name}, {formatDate(row.next_fixture.date)}
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function InferredRows({ rows }: { rows: AnalysisInference[] }) {
  if (!rows.length) {
    return (
      <p className="fine-print">
        No inferred absence at the current thresholds. A row here means not in the last two
        matchday squads; cause is not published and it is not a medical diagnosis.
      </p>
    );
  }
  return (
    <ul className="plain-list">
      {rows.map((row) => (
        <li key={row.player_id}>
          <Link href={`/players/${row.player_id}/`}>{row.player_name ?? row.player_id}</Link>{" "}
          <span className="muted">
            · {row.role_label ?? "role unknown"} · not in the last two matchday squads
            {row.fixtures.length
              ? ` (${row.fixtures.map((fixture) => formatDate(fixture.date)).join(", ")})`
              : ""}
            · {row.in_squad_of_six}/6 in squad
          </span>{" "}
          <span className="badge badge-neutral">{row.confidence} · cause not published</span>
        </li>
      ))}
    </ul>
  );
}

function SelectionRows({ rows }: { rows: AnalysisSelection[] }) {
  if (!rows.length) return <p className="fine-print">No selection-watch candidate at current coverage.</p>;
  return (
    <ul className="plain-list">
      {rows.map((row) => (
        <li key={String(row.player_id ?? row.player_name)}>
          {row.player_id ? (
            <Link href={`/players/${row.player_id}/`}>{row.player_name ?? row.player_id}</Link>
          ) : (
            row.player_name
          )}{" "}
          <span className="muted">
            · {row.role_label ?? "role unknown"} · {row.confidence} contender
            {row.score !== null ? ` · score ${formatDecimal(row.score, 2)}` : ""}
          </span>{" "}
          <span className="badge badge-neutral">projection, not team news</span>
        </li>
      ))}
    </ul>
  );
}

function AimsTable({ rows }: { rows: AnalysisAim[] }) {
  return (
    <div className="table-wrap">
      <table className="league-table compact">
        <caption className="fine-print">
          Analyst-set baseline, not a published club target.
        </caption>
        <thead>
          <tr>
            <th scope="col">Aim</th>
            <th scope="col">Target</th>
            <th scope="col">Current</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.label}</td>
              <td>{row.target}</td>
              <td>{row.current}</td>
              <td>
                {row.status.replaceAll("_", " ")}
                {row.gap !== null ? <span className="muted"> · gap {row.gap}</span> : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LensTable({ lens }: { lens: AnalysisLens }) {
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <p className="eyebrow">{lens.label}</p>
          <h3>
            {lens.count} meet · {lens.rows.length} shown
          </h3>
        </div>
      </div>
      <p className="fine-print">{lens.definition}</p>
      {lens.rows.length ? (
        <div className="table-wrap">
          <table className="league-table compact">
            <caption className="fine-print">
              Measured screening lens. No valuation, fee, wage or contract claim.
            </caption>
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th className="num" scope="col">Age</th>
                <th scope="col">Role</th>
                <th className="num" scope="col">Mins</th>
                <th className="num" scope="col">Share</th>
                <th className="num" scope="col">Percentile</th>
                <th className="num" scope="col">Cohort n</th>
              </tr>
            </thead>
            <tbody>
              {lens.rows.map((row) => (
                <tr key={`${lens.label}-${row.player_id}`}>
                  <td>
                    <Link href={`/players/${row.player_id}/`}>{row.player_name ?? row.player_id}</Link>
                  </td>
                  <td className="num">{row.age ?? "—"}</td>
                  <td>{row.role_label ?? "—"}</td>
                  <td className="num">{formatInteger(row.minutes)}</td>
                  <td className="num">
                    {row.minutes_share === null ? "—" : formatPercentValue(row.minutes_share * 100, 1)}
                  </td>
                  <td className="num">
                    {row.rating_percentile === null ? "—" : formatPercentValue(row.rating_percentile, 1)}
                  </td>
                  <td className="num">{row.cohort_n ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="fine-print">No player meets this lens at the current thresholds.</p>
      )}
    </section>
  );
}

function rankingReason(reason: string | null): string {
  switch (reason) {
    case "below_min_team_matches":
      return "Not enough matches have been played to rank the league.";
    case "provider_coverage_incomplete":
      return "Provider xG coverage is incomplete, so ranks are withheld; values that are present are shown.";
    case "possession_coverage_incomplete":
      return "Possession coverage is incomplete, so ranks are withheld; values that are present are shown.";
    case "league_table_incomplete":
      return "The league table is incomplete, so ranks are withheld.";
    case "league_table_unavailable":
      return "No Premiership league table is available in this build.";
    case "league_rankings_build_failed":
      return "League rankings could not be built in this publish.";
    default:
      return "";
  }
}

function metricValue(metricId: string, value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (metricId === "possession_pct") return formatPercentValue(value, 2);
  if (metricId === "gd_pm") return formatSigned(value, 2);
  return formatDecimal(value, 2);
}

function LeagueRankingsSections({ rankings }: { rankings: AnalysisLeagueRankings }) {
  const aberdeen = rankings.aberdeen;
  const available = rankings.state === "available";
  const badge = available
    ? `Within-Premiership ranks · ${formatInteger(rankings.league_size)} teams`
    : rankings.state === "partial"
      ? "Partial coverage"
      : "Unavailable";
  const coverage = rankings.coverage ?? {};
  const provider = coverage.provider_xg ?? {};
  const possession = coverage.possession ?? {};
  const providerCovered = Number(provider.team_rows ?? 0);
  const providerTotal = Number(provider.team_rows_total ?? 0);
  const possessionCovered = Number(possession.team_rows ?? 0);
  const possessionTotal = Number(possession.team_rows_total ?? 0);
  const context = aberdeen?.context;
  const summaryRows = rankings.metrics;
  const teamRows = rankings.teams;

  return (
    <>
      <section className="section" data-contract="analysis.league-rankings">
        <div className="section-head">
          <div>
            <p className="eyebrow">
              Season so far · {rankings.competition_name ?? "Scottish Premiership"}
            </p>
            <h2>Where Aberdeen rank</h2>
          </div>
          <span className="badge badge-neutral">{badge}</span>
        </div>
        <p className="fine-print">
          {rankings.scope_label}. Rank is 1 plus the number of teams with a better
          published value; ties share the better rank. A missing value is unknown,
          not zero.
        </p>
        {!available && rankingReason(rankings.reason) ? (
          <p className="fine-print" data-contract-indicator="unknown">
            {rankingReason(rankings.reason)}
          </p>
        ) : null}
        <TableFrame label="Aberdeen's within-Premiership ranks with league median and leader">
          <table className="league-table compact">
            <caption className="fine-print">
              Provider xG is football-data.co.uk with API-Football fallback (
              {formatInteger(providerCovered)}/{formatInteger(providerTotal)} team
              rows). Possession is provider-reported ({formatInteger(possessionCovered)}/
              {formatInteger(possessionTotal)} team rows) and is not used in the
              matchday style lean. Scope: {rankings.scope_label.toLowerCase()};
              per-match rates. As of {formatDate(rankings.as_of)}.
            </caption>
            <thead>
              <tr>
                <th scope="col">Metric</th>
                <th scope="col" className="num">
                  Aberdeen
                </th>
                <th scope="col" className="num">
                  Rank
                </th>
                <th scope="col">Direction</th>
                <th scope="col" className="num">
                  League median
                </th>
                <th scope="col">Leader</th>
              </tr>
            </thead>
            <tbody>
              {summaryRows.length === 0 ? (
                <tr>
                  <td>Unavailable</td>
                  <td className="num">—</td>
                  <td className="num">—</td>
                  <td>—</td>
                  <td className="num">—</td>
                  <td>—</td>
                </tr>
              ) : (
                summaryRows.map((metric) => {
                  const value = aberdeen?.values?.[metric.id];
                  const rank = aberdeen?.ranks?.[metric.id];
                  const league = rankings.league?.[metric.id];
                  const leaderNames = (league?.leader_teams ?? [])
                    .map((team) => team.team_name)
                    .join(", ");
                  return (
                    <tr key={metric.id}>
                      <td>
                        {metric.label}{" "}
                        <span className="muted">({metric.source_label})</span>
                      </td>
                      <td className="num">{metricValue(metric.id, value)}</td>
                      <td className="num">
                        {rank === null || rank === undefined
                          ? "—"
                          : `${ordinal(rank)} of ${formatInteger(rankings.league_size)}`}
                      </td>
                      <td>{metric.direction_label}</td>
                      <td className="num">
                        {metricValue(metric.id, league?.median)}
                      </td>
                      <td>
                        {leaderNames
                          ? `${leaderNames} ${metricValue(metric.id, league?.leader_value)}`
                          : "—"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </TableFrame>
        {context ? (
          <p className="fine-print">
            Aberdeen&apos;s fitba fxG is {formatDecimal(context.fxg, 2)} over{" "}
            {formatInteger(context.matches ?? 0)} league matches ({formatInteger(context.goals)}{" "}
            goals, {formatSigned(context.goals_minus_fxg ?? 0, 2)} goals minus fxG). It is a
            local model shown for context, not part of the provider-xG rank.{" "}
            <Link className="text-link" href="/analysis/xg/">
              fxG model →
            </Link>
          </p>
        ) : null}
        <p className="fine-print">
          Provider xG is one provider&apos;s model, not fitba fxG; the two are never
          blended. Possession is provider-reported and is not used in the matchday
          style lean.
        </p>
      </section>

      <section className="section" data-contract="analysis.league-table">
        <div className="section-head">
          <div>
            <p className="eyebrow">The league, ranked</p>
            <h2>The Premiership, ranked</h2>
          </div>
          <span className="badge badge-neutral">
            {formatInteger(rankings.league_size)} teams · {formatInteger(rankings.matches)}{" "}
            matches
          </span>
        </div>
        <TableFrame label="Scottish Premiership table with per-match goals, xG, xGA, possession and points">
          <table className="league-table compact">
            <caption className="fine-print">
              Per-match rates within the {rankings.competition_name} only. Provider xG
              is football-data.co.uk with API-Football fallback; possession is
              provider-reported. P = played, Pts = league points. A missing value is
              unknown, not zero. As of {formatDate(rankings.as_of)}.
            </caption>
            <thead>
              <tr>
                <th scope="col" className="num">
                  #
                </th>
                <th scope="col">Team</th>
                <th scope="col" className="num">
                  P
                </th>
                <th scope="col" className="num">
                  GF/m
                </th>
                <th scope="col" className="num">
                  GA/m
                </th>
                <th scope="col" className="num">
                  xG/m
                </th>
                <th scope="col" className="num">
                  xGA/m
                </th>
                <th scope="col" className="num">
                  Poss %
                </th>
                <th scope="col" className="num">
                  Pts
                </th>
              </tr>
            </thead>
            <tbody>
              {teamRows.length === 0 ? (
                <tr>
                  <td className="num">—</td>
                  <td>No league table published</td>
                  <td className="num">—</td>
                  <td className="num">—</td>
                  <td className="num">—</td>
                  <td className="num">—</td>
                  <td className="num">—</td>
                  <td className="num">—</td>
                  <td className="num">—</td>
                </tr>
              ) : (
                teamRows.map((team) => {
                  const isAberdeen = team.team_id === "sco:aberdeen";
                  return (
                    <tr key={team.team_id} className={isAberdeen ? "is-highlight" : undefined}>
                      <td className="num">{team.position ?? "—"}</td>
                      <td>{team.team_name}</td>
                      <td className="num">{formatInteger(team.played)}</td>
                      <td className="num">{metricValue("goals_for_pm", team.values.goals_for_pm)}</td>
                      <td className="num">
                        {metricValue("goals_against_pm", team.values.goals_against_pm)}
                      </td>
                      <td className="num">{metricValue("xg_for_pm", team.values.xg_for_pm)}</td>
                      <td className="num">
                        {metricValue("xg_against_pm", team.values.xg_against_pm)}
                      </td>
                      <td className="num">
                        {metricValue("possession_pct", team.values.possession_pct)}
                      </td>
                      <td className="num">
                        {team.points === null || team.points === undefined
                          ? "—"
                          : formatInteger(team.points)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </TableFrame>
      </section>
    </>
  );
}

export default function AnalysisPage() {
  const data = getAnalysisSummary();
  if (!data) {
    return (
      <ContractPage surface="analysis" state="empty">
        <section className="page-head" data-contract="analysis.hero">
          <p className="eyebrow">Analysis</p>
          <h1>Season overview</h1>
          <p className="lede">
            No season overview is published in this build. Run <code>uv run fitba publish</code>.
          </p>
        </section>
      </ContractPage>
    );
  }
  const hero = data.hero;
  const counts = data.availability.counts;
  const review = data.availability.review ?? {
    status: "ok",
    count: 0,
    contradicted: 0,
    aging: 0,
    suspension_served: 0,
    ledger: {},
    rows: [],
  };
  const lenses = Object.values(data.squad_decisions.lenses ?? {});
  return (
    <ContractPage surface="analysis">
      <section className="page-head" data-contract="analysis.hero">
        <p className="eyebrow">Season {data.season} · {hero.league_name ?? "Scottish Premiership"}</p>
        <h1>Season overview</h1>
        <p className="lede">
          {ordinal(hero.position)} · {formatInteger(hero.points ?? 0)} points from{" "}
          {formatInteger(hero.played ?? 0)} · form {hero.form ?? "—"} · goal difference{" "}
          {hero.goal_difference ?? "—"}.
        </p>
        <p className="fine-print">
          Evidence, coverage and unknown states are shown beside each block.{" "}
          <Link className="text-link" href="/methodology/">Method →</Link>{" "}
          <Link className="text-link" href="/sources/">Sources →</Link>{" "}
          <Link className="text-link" href="/claims/">Claims and evidence →</Link>
        </p>
      </section>

      {data.league_rankings ? (
        <LeagueRankingsSections rankings={data.league_rankings} />
      ) : null}

      <section className="section" data-contract="analysis.next-up">
        <div className="section-head">
          <div>
            <p className="eyebrow">Next up</p>
            <h2>The next three</h2>
          </div>
          <span className="badge badge-neutral">Competitive only</span>
        </div>
        <FixtureTable rows={data.next_up} />
        <p className="back-link">
          <Link href="/matchday/">Next six on matchday →</Link>
          {" · "}
          <Link href="/matches/">Full schedule →</Link>
        </p>
      </section>

      <section className="section" data-contract="analysis.availability">
        <div className="section-head">
          <div>
            <p className="eyebrow">Availability and selection</p>
            <h2>Who is out, who is a doubt, who is next in line</h2>
          </div>
          <span className="badge badge-neutral">
            {counts.out_official ?? 0} out · {counts.available ?? 0} reported available ·{" "}
            {counts.unknown ?? 0} no verified news
          </span>
        </div>
        <div className="stat-row four">
          <div className="stat-tile">
            <span className="stat-label">Known unavailable</span>
            <span className="stat-value">{formatInteger(counts.out_official ?? 0)}</span>
            <span className="stat-note">official AFC team news</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Reported available</span>
            <span className="stat-value">{formatInteger(counts.available ?? 0)}</span>
            <span className="stat-note">not a medical clearance</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">No verified news</span>
            <span className="stat-value">{formatInteger(counts.unknown ?? 0)}</span>
            <span className="stat-note">not “fit”</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Loans out</span>
            <span className="stat-value">{formatInteger(counts.loans_out ?? 0)}</span>
            <span className="stat-note">shown separately</span>
          </div>
        </div>
        <p className="fine-print">
          “Available” means a verified ledger entry, not fit. The active analysis universe is{" "}
          {formatInteger(counts.active ?? 0)}: current squad plus ledger-only Tobers. Full roster:{" "}
          <Link className="text-link" href="/squad/">Squad →</Link>
        </p>
        <h3>Official team news</h3>
        <OfficialTable rows={data.availability.official} />
        <div data-contract="analysis.availability.review">
          <h3>Team news needing review</h3>
          <p className="fine-print">
            {formatInteger(review.count)} claims need review:{" "}
            {formatInteger(review.contradicted)} contradicted and{" "}
            {formatInteger(review.aging)} aging; {formatInteger(review.suspension_served)}{" "}
            suspension served.
          </p>
          <ReviewTable review={review} />
        </div>
        <h3>Derived selection signals</h3>
        <p className="fine-print">
          Competition-scoped and labelled. Projected or review states are not official team news.
        </p>
        <SuspensionRows rows={data.availability.suspensions} />
        <InferredRows rows={data.availability.inferred} />
        <h3>Selection watch</h3>
        <SelectionRows rows={data.availability.selection} />
      </section>

      <section className="section" data-contract="analysis.aims">
        <div className="section-head">
          <div>
            <p className="eyebrow">Season aims</p>
            <h2>What this season is for</h2>
          </div>
          <span className="badge badge-neutral">Analyst-set, not a club target</span>
        </div>
        <AimsTable rows={data.aims} />
      </section>

      <section className="section" data-contract="analysis.squad-decisions">
        <div className="section-head">
          <div>
            <p className="eyebrow">Squad decisions</p>
            <h2>Age, minutes and role</h2>
          </div>
          <span className="badge badge-neutral">
            {data.squad_decisions.coverage.with_percentile ?? 0}/
            {data.squad_decisions.coverage.active_players ?? 0} with percentile ·{" "}
            {data.squad_decisions.coverage.without_stats ?? 0} without stats
          </span>
        </div>
        <p className="fine-print">
          Screening lenses, not valuations or predictions.{" "}
          {data.squad_decisions.contract.note} Loan-outs:{" "}
          {formatInteger(data.squad_decisions.loans.length)}; end dates are not held.
        </p>
        <div className="grid two-col">
          {lenses.map((lens) => (
            <LensTable key={lens.label} lens={lens} />
          ))}
        </div>
      </section>

      <section className="section" data-contract="analysis.bridges">
        <div className="section-head">
          <div>
            <p className="eyebrow">Matchday, squad and scouting</p>
            <h2>Where the evidence lives</h2>
          </div>
        </div>
        <div className="grid two-col">
          {data.bridges.map((bridge) => (
            <section className="card" key={bridge.href}>
              <p className="eyebrow">{bridge.label}</p>
              <h3>
                <Link href={bridge.href}>{bridge.label}</Link>
              </h3>
              <p>{bridge.summary}</p>
            </section>
          ))}
        </div>
        <p className="back-link">
          <Link href="/matches/">Results and fixtures →</Link>
          {" · "}
          <Link href="/analysis/xg/">fxG model →</Link>
          {" · "}
          <Link href="/transfers/">Confirmed business →</Link>
        </p>
      </section>

      <section className="section" data-contract="analysis.coverage">
        <div className="section-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>What this page can and cannot say</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table className="league-table compact">
            <caption className="fine-print">
              Coverage and unknowns. A missing value is a gap, not zero.
            </caption>
            <thead>
              <tr>
                <th scope="col">Data</th>
                <th scope="col">Covered</th>
                <th scope="col">Unknown or gap</th>
                <th scope="col">Limit</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Availability ledger</td>
                <td>{formatInteger(data.coverage.availability.known)}</td>
                <td>{formatInteger(data.coverage.availability.unknown)}</td>
                <td>active universe {formatInteger(data.coverage.availability.active)}</td>
              </tr>
              <tr>
                <td>Card events</td>
                <td>
                  {Object.values(data.coverage.cards ?? {})
                    .map((item) => `${item.covered}/${item.played}`)
                    .join(" · ")}
                </td>
                <td>
                  {Object.entries(data.coverage.cards ?? {})
                    .filter(([, item]) => !item.complete)
                    .map(([key]) => key)
                    .join(", ") || "none"}
                </td>
                <td>competition-scoped; unverified rules are review-only</td>
              </tr>
              <tr>
                <td>Named benches</td>
                <td>{formatInteger(data.coverage.bench?.named_bench_complete ?? 0)}</td>
                <td>{formatInteger(data.coverage.bench?.fixtures ?? 0)}</td>
                <td>at least seven named substitutes per side</td>
              </tr>
              <tr>
                <td>Fixture schedule</td>
                <td>{formatInteger(data.coverage.schedule?.scheduled ?? 0)}</td>
                <td>{formatInteger(data.coverage.schedule?.conflicts ?? 0)}</td>
                <td>conflict-review rows are excluded from lookaheads</td>
              </tr>
            </tbody>
          </table>
        </div>
        <ul className="plain-list">
          {(data.coverage.limitations ?? []).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </ContractPage>
  );
}
