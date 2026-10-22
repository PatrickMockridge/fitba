import { notFound } from "next/navigation";
import Link from "next/link";
import { FormStrip } from "@/components/FormStrip";
import { ManagerRecordTable } from "@/components/ManagerRecordTable";
import { StatTile } from "@/components/StatTile";
import {
  formatDate,
  getAberdeen,
  getHistory,
  getHistorySeason,
  getTransfers,
} from "@/lib/data";

export const dynamicParams = false;

export function generateStaticParams() {
  const history = getHistory();
  return (history?.seasons ?? []).map(({ season }) => ({ season }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ season: string }>;
}) {
  const { season } = await params;
  const doc = getHistorySeason(season);
  const title = `${season} season review · fitba`;
  const description = doc?.headline
    ? `${doc.headline} The measured season record and the labelled assessment.`
    : `The ${season} season record and assessment.`;
  return {
    title,
    description,
    alternates: { canonical: `/history/${season}/` },
    openGraph: { title, description, type: "article" },
    twitter: { card: "summary", title, description },
  };
}

function pct(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

function money(value: number) {
  return `${value < 0 ? "−" : ""}£${Math.abs(value).toLocaleString("en-GB")}`;
}

function moneyRange(low: number | null | undefined, high: number | null | undefined) {
  if (low === null || low === undefined || high === null || high === undefined) {
    return "—";
  }
  return `${money(low)} – ${money(high)}`;
}

function value(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "—";
  return value.toFixed(digits);
}

function outcomeBadge(outcome: string) {
  if (outcome === "won") return "badge-ok";
  if (outcome === "pending") return "badge-warn";
  if (outcome === "not_entered") return "badge-neutral";
  return "badge-neutral";
}

function ordinal(value: number) {
  const suffix =
    value === 1 ? "st" : value === 2 ? "nd" : value === 3 ? "rd" : "th";
  return `${value}${suffix}`;
}

export default async function HistorySeasonPage({
  params,
}: {
  params: Promise<{ season: string }>;
}) {
  const { season } = await params;
  const doc = getHistorySeason(season);
  const aberdeen = getAberdeen();
  if (!doc) notFound();
  const league = aberdeen?.history.find((row) => row.season === season) ?? null;
  const history = getHistory();
  const transferMap = new Map(
    (getTransfers()?.transfers ?? []).map((transfer) => [
      transfer.transfer_id,
      transfer,
    ]),
  );
  const keyTransfers = [
    ...(doc.key_transfers.arrivals ?? []).map((id) => ({ id, direction: "in" as const })),
    ...(doc.key_transfers.departures ?? []).map((id) => ({ id, direction: "out" as const })),
  ]
    .map(({ id, direction }) => {
      const transfer = transferMap.get(id);
      return transfer ? { ...transfer, direction } : null;
    })
    .filter((transfer): transfer is NonNullable<typeof transfer> => transfer !== null);
  const index = history?.seasons.findIndex((item) => item.season === season) ?? -1;
  const previous = index > 0 ? history?.seasons[index - 1] : null;
  const next =
    history && index >= 0 && index < history.seasons.length - 1
      ? history.seasons[index + 1]
      : null;
  const managerNames = [
    ...new Set(
      doc.managers
        .map((manager) => manager.name)
        .filter((name): name is string => Boolean(name)),
    ),
  ].join(", ");

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">
          The record · {doc.status === "in_progress" ? "In progress" : "Completed season"}
        </p>
        <h1>{doc.season}</h1>
        <p className="lede">{doc.headline}</p>
        <div className="hero-actions">
          <span className={`badge ${doc.status === "in_progress" ? "badge-warn" : "badge-ok"}`}>
            {doc.status === "in_progress" ? `As of ${doc.as_of}` : "End-of-season review"}
          </span>
          {league ? (
            <span className="badge badge-neutral">
              {ordinal(league.position)} · {league.points} pts
            </span>
          ) : null}
          <span className="badge badge-neutral">
            {history?.seasons.find((item) => item.season === season)?.competition_name ??
              "League"}
          </span>
          <span className="badge badge-neutral">{managerNames || "Manager unknown"}</span>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Expectations</p>
            <h2>The baseline going in</h2>
          </div>
          <span className="badge badge-warn">Curated</span>
        </div>
        <p>{String(doc.expectations.baseline ?? "")}</p>
        <p>{String(doc.expectations.target ?? "")}</p>
        <p className="fine-print">{String(doc.expectations.context ?? "")}</p>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Measured</p>
            <h2>The league record</h2>
          </div>
          <span className="badge badge-neutral">Joined from the club payload</span>
        </div>
        {league ? (
          <div className="stat-row four">
            <StatTile label="Position" value={league.position} note={`${league.played} played`} />
            <StatTile label="Points" value={league.points} note={`${league.gd > 0 ? "+" : ""}${league.gd} GD`} />
            <StatTile label="Form" value={<FormStrip form={league.form} />} note="Most recent first" />
            <StatTile
              label="Record"
              value={`${doc.managers.reduce((sum, manager) => sum + manager.won, 0)}-${doc.managers.reduce(
                (sum, manager) => sum + manager.drawn,
                0,
              )}-${doc.managers.reduce((sum, manager) => sum + manager.lost, 0)}`}
              note="League W-D-L"
            />
          </div>
        ) : (
          <p className="muted">League baseline unavailable for this season.</p>
        )}
        <p className="fine-print">
          Manager records are league-only. Cup and European results are curated
          exit rounds, not match-level manager records.
        </p>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">The season</p>
            <h2>Managers and the within-season split</h2>
          </div>
        </div>
        <ManagerRecordTable records={doc.managers} />
        <p className="fine-print">
          Interim spells are separate records. A match in a gap is not assigned
          to the nearest manager.
        </p>
      </section>

      <div className="grid two-col">
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Cups</p>
              <h2>Domestic runs</h2>
            </div>
          </div>
          {doc.cup_runs.length ? (
            <ul className="plain-list">
              {doc.cup_runs.map((run) => (
                <li key={`${run.competition_id}-${run.exit_round}`}>
                  <strong>{run.competition_name ?? run.competition_id}</strong> ·{" "}
                  {run.exit_round}{" "}
                  <span className={`badge ${outcomeBadge(run.outcome)}`}>{run.outcome}</span>
                  {run.note ? <span className="fine-print"> {run.note}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No cup runs are recorded.</p>
          )}
        </section>

        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Europe</p>
              <h2>Continental runs</h2>
            </div>
          </div>
          {doc.europe.length ? (
            <ul className="plain-list">
              {doc.europe.map((run) => (
                <li key={`${run.competition_id}-${run.stage_reached ?? run.exit_round}`}>
                  <strong>{run.competition_name ?? run.competition_id}</strong> ·{" "}
                  {run.stage_reached ?? run.exit_round}{" "}
                  <span className={`badge ${outcomeBadge(run.outcome)}`}>{run.outcome}</span>
                  {run.note ? <span className="fine-print"> {run.note}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Not in European competition.</p>
          )}
        </section>
      </div>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Recruitment</p>
            <h2>What came in and went out</h2>
          </div>
          <span className="badge badge-neutral">
            {doc.recruitment.coverage === "audited" ? "Audited" : "Curated partial"}
          </span>
        </div>
        <div className="stat-row four">
          <StatTile label="Arrivals" value={doc.recruitment.arrivals} note={`${doc.recruitment.permanent_in} permanent`} />
          <StatTile label="Departures" value={doc.recruitment.departures} note={`${doc.recruitment.permanent_out} permanent`} />
          <StatTile label="Loans" value={`${doc.recruitment.loans_in} in / ${doc.recruitment.loans_out} out`} note="register" />
          <StatTile
            label="Estimated net"
            value={moneyRange(
              doc.recruitment.valuation?.fee_low_gbp,
              doc.recruitment.valuation?.fee_high_gbp,
            )}
            note={`inferred · ${doc.recruitment.valuation?.confidence ?? "low"} confidence · ${
              (doc.recruitment.valuation?.counts?.disclosed ?? 0) +
              (doc.recruitment.valuation?.counts?.reported ?? 0)
            } known · ${doc.recruitment.valuation?.counts?.modelled ?? 0} modelled · negative = income`}
          />
        </div>
        <p className="fine-print">
          Estimated net is a range from public/reported fee anchors and a
          transparent age, position and market model. It is not an audited
          balance; free transfers count as zero fee and loan fees are excluded.
        </p>
        <div className="grid two-col">
          <div>
            <p className="eyebrow">Source market</p>
            <ul className="plain-list">
              {doc.recruitment.market_mix.map((market) => (
                <li key={market.market}>
                  <strong>{market.market}</strong> · {market.arrivals} arrivals{" "}
                  <span className="fine-print">{pct(market.share)}</span>
                </li>
              ))}
            </ul>
            <p className="fine-print">
              {doc.recruitment.market_unknown_count}{" "}
              {doc.recruitment.market_unknown_count === 1 ? "arrival has" : "arrivals have"}{" "}
              no resolved source market.
            </p>
          </div>
          <div>
            <p className="eyebrow">Age at arrival</p>
            <p>
              Median <strong>{doc.recruitment.median_age ?? "—"}</strong> · average{" "}
              <strong>{doc.recruitment.average_age ?? "—"}</strong> · coverage{" "}
              {pct(doc.recruitment.age_coverage)}.
            </p>
            <p className="fine-print">{doc.recruitment.note}</p>
          </div>
        </div>
        {keyTransfers.length ? (
          <div className="mini-block">
            <p className="eyebrow">Key business</p>
            <ul className="plain-list">
              {keyTransfers.map((transfer) => (
                <li key={transfer.transfer_id}>
                  <span className={`badge ${transfer.direction === "in" ? "badge-ok" : "badge-neutral"}`}>
                    {transfer.direction === "in" ? "IN" : "OUT"}
                  </span>{" "}
                  <strong>{transfer.player_name}</strong> · {transfer.from_club_name} →{" "}
                  {transfer.to_club_name} · {transfer.fee_display}{" "}
                  <Link className="text-link" href="/transfers/">
                    register
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="fine-print">
          {doc.key_transfers.note ?? ""}{" "}
          <Link className="text-link" href="/transfers/">
            Full transfer register →
          </Link>
        </p>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Style</p>
            <h2>How the season looked</h2>
          </div>
          <span className="badge badge-neutral">{doc.style.coverage}</span>
        </div>
        <div className="stat-row four">
          <StatTile
            label="Shots for / against"
            value={`${value(doc.style.shots_for_pm)} / ${value(doc.style.shots_against_pm)}`}
            note="per league match"
          />
          <StatTile
            label="Shots on target"
            value={`${value(doc.style.shots_on_target_for_pm)} / ${value(doc.style.shots_on_target_against_pm)}`}
            note="per league match"
          />
          <StatTile
            label="Shot accuracy"
            value={pct(doc.style.shot_accuracy)}
            note="shots on target / shots"
          />
          <StatTile
            label="Goals for / against"
            value={`${value(doc.style.goals_for_pm)} / ${value(doc.style.goals_against_pm)}`}
            note="per league match"
          />
        </div>
        <p className="fine-print">{doc.style.note}</p>
        <p className="fine-print">{doc.tactical.style_note}</p>
        <p className="fine-print">
          Possession is not shown unless the provider team-statistics backfill
          is available; it is never inferred.
        </p>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Selection</p>
            <h2>Who played, and how old they were</h2>
          </div>
          <span className="badge badge-neutral">
            {doc.selection.status === "available" ? "Measured" : "Partial"}
          </span>
        </div>
        {doc.selection.status === "unavailable" ? (
          <p className="muted">
            {doc.selection.note ?? "Historical lineups are unavailable for this season."}
          </p>
        ) : (
          <>
            <div className="stat-row four">
              <StatTile
                label="Players used"
                value={doc.selection.players_used ?? "—"}
                note={`${doc.selection.fixtures_with_lineups ?? 0}/${doc.selection.fixtures_total ?? 0} fixtures`}
              />
              <StatTile
                label="Average starter age"
                value={doc.selection.average_starter_age ?? "—"}
                note={`age coverage ${pct(doc.selection.age_coverage)}`}
              />
              <StatTile
                label="U21 minutes"
                value={pct(doc.selection.u21_minutes_share)}
                note="share of known-age minutes"
              />
              <StatTile
                label="Lineup coverage"
                value={pct(doc.selection.lineup_coverage)}
                note="historical backfill"
              />
            </div>
            <div className="grid two-col">
              <div>
                <p className="eyebrow">Formation mix</p>
                <ul className="plain-list">
                  {(doc.selection.formation_mix ?? []).slice(0, 6).map((formation) => (
                    <li key={formation.formation}>
                      <strong>{formation.formation === "unknown" ? "No grid" : formation.formation}</strong> ·{" "}
                      {formation.fixtures} fixtures ({pct(formation.share)})
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="eyebrow">Top by starts</p>
                <div className="table-wrap">
                  <table className="league-table compact">
<caption className="fine-print">Season record, managers, staff and selection.</caption>
                    <thead>
                      <tr>
                        <th>Player</th>
                        <th className="num">Starts</th>
                        <th className="num">Mins</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(doc.selection.top_by_starts ?? []).slice(0, 11).map((player) => (
                        <tr key={player.player_id}>
                          <td>{player.player_name ?? player.player_id}</td>
                          <td className="num">{player.starts}</td>
                          <td className="num">{player.minutes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            <p className="fine-print">{doc.selection.note}</p>
            <p className="fine-print">{doc.tactical.selection_note}</p>
          </>
        )}
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Academy</p>
            <h2>Youth pathway</h2>
          </div>
        </div>
        <div className="grid two-col">
          <div>
            <p className="eyebrow">Curated debuts</p>
            {doc.academy.debuts.length ? (
              <ul className="plain-list">
                {doc.academy.debuts.map((debut, index) => (
                  <li key={`${String(debut.player_name)}-${index}`}>
                    <strong>{String(debut.player_name)}</strong>{" "}
                    {debut.debut_date ? `· ${String(debut.debut_date)}` : ""}
                    {debut.note ? <span className="fine-print"> {String(debut.note)}</span> : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No curated academy debut is recorded for this season.</p>
            )}
          </div>
          <div>
            <p className="eyebrow">Measured new players</p>
            {doc.academy.measured_new_players.length ? (
              <ul className="plain-list">
                {doc.academy.measured_new_players.map((player, index) => (
                  <li key={`${String(player.player_id)}-${index}`}>
                    <strong>{String(player.player_name ?? player.player_id)}</strong>{" "}
                    {player.date ? `· ${formatDate(String(player.date).slice(0, 10))}` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">
                {doc.academy.debut_basis === "not_computed"
                  ? "New-player measurement starts in the following season."
                  : "No measured new players."}
              </p>
            )}
          </div>
        </div>
        <p className="fine-print">{doc.academy.note}</p>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Off the pitch</p>
            <h2>Staff changes</h2>
          </div>
        </div>
        {doc.staff_changes.length ? (
          <ul className="plain-list">
            {doc.staff_changes.map((change, index) => (
              <li key={`${change.stint_id}-${change.date}-${index}`}>
                <span className="match-date">{formatDate(change.date.slice(0, 10))}</span>{" "}
                <strong>{change.name}</strong> · {change.role}{" "}
                <span className={`badge ${change.change === "in" ? "badge-ok" : "badge-neutral"}`}>
                  {change.change === "in" ? "In" : "Out"}
                </span>
                {change.interim ? <span className="badge badge-warn">Interim</span> : null}
                {change.change === "out" && change.reason_out ? (
                  <span className="fine-print"> {change.reason_out}</span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No key staff change is recorded for this season.</p>
        )}
      </section>

      {doc.review ? (
        <section className="card read-block">
          <p className="eyebrow">
            The read ·{" "}
            {doc.review.label === "curated_editorial"
              ? "fitba assessment"
              : doc.review.label}
          </p>
          <h2>An assessment, not a measurement</h2>
          <p><strong>What worked.</strong> {doc.review.what_worked}</p>
          <p><strong>What did not.</strong> {doc.review.what_did_not}</p>
          <p><strong>The trade-off.</strong> {doc.review.trade_off}</p>
          <p>{doc.review.read}</p>
          <p className="fine-print"><strong>Look ahead.</strong> {doc.review.look_ahead}</p>
        </section>
      ) : (
        <section className="card read-block">
          <p className="eyebrow">Season in progress</p>
          <h2>No final verdict yet</h2>
          <p>{doc.interim_read}</p>
          <p className="fine-print">
            The final review is published at the end of the season. Until then,
            the measured record and the coverage notes are the output.
          </p>
        </section>
      )}

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>What is measured, curated and missing</h2>
          </div>
          <span className="badge badge-neutral">Reviewed {doc.reviewed_at}</span>
        </div>
        <ul className="plain-list">
          <li><strong>League record:</strong> {doc.coverage.league_record}</li>
          <li><strong>Manager records:</strong> {doc.coverage.manager_scope} only</li>
          <li><strong>Transfers:</strong> {doc.coverage.transfers}</li>
          <li>
            <strong>Lineups:</strong> {doc.coverage.history.status} ·{" "}
            {doc.coverage.history.fixtures_with_lineups}/{doc.coverage.history.fixtures_total} fixtures
          </li>
          <li><strong>Unattributed league matches:</strong> {doc.coverage.unattributed_matches}</li>
        </ul>
        <p className="fine-print">{doc.coverage.note}</p>
        <p className="fine-print">
          Sources:{" "}
          {doc.sources.map((source, index) => (
            <span key={source.url}>
              {index ? " · " : ""}
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.id}
              </a>
            </span>
          ))}
        </p>
      </section>

      <p className="back-link">
        {previous ? <Link href={previous.href}>← {previous.season}</Link> : null}
        {previous && next ? " · " : null}
        {next ? <Link href={next.href}>{next.season} →</Link> : null}
        {" · "}
        <Link href="/history/">The record</Link>
        {" · "}
        <Link href="/matches/">Match record</Link>
      </p>
    </>
  );
}
