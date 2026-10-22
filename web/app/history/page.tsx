import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { HonoursCabinet } from "@/components/HonoursCabinet";
import { HistoryTimeline } from "@/components/HistoryTimeline";
import { ManagerRecordTable } from "@/components/ManagerRecordTable";
import { StatTile } from "@/components/StatTile";
import {
  formatDate,
  getAberdeen,
  getHistory,
  getManifest,
  type HistorySeasonRef,
} from "@/lib/data";

export const metadata = { title: "The Cormack era · fitba" };

function money(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  const sign = value < 0 ? "−" : "";
  return `${sign}£${Math.abs(value).toLocaleString("en-GB")}`;
}

function moneyRange(low: number | null | undefined, high: number | null | undefined) {
  if (low === null || low === undefined || high === null || high === undefined) {
    return "—";
  }
  return `${money(low)} – ${money(high)}`;
}

function personNames(
  history: NonNullable<ReturnType<typeof getHistory>>,
) {
  const names = new Map<string, string>();
  for (const person of history.staff) {
    names.set(person.person_id, person.name);
  }
  return names;
}

function seasonStatusLabel(status: HistorySeasonRef["status"]) {
  return status === "in_progress" ? "In progress" : "Completed";
}

export default function HistoryPage() {
  const history = getHistory();
  const aberdeen = getAberdeen();
  const manifest = getManifest();
  if (!history) {
    return (
      <ContractPage surface="history" state="empty">
        <section className="empty-state" data-contract="history.empty">
          <h1>No historical record published</h1>
          <p>
            Run <code>uv run fitba publish</code> after curating the history
            register.
          </p>
        </section>
      </ContractPage>
    );
  }
  const names = personNames(history);
  const clubHistory = new Map(
    (aberdeen?.history ?? []).map((row) => [row.season, row]),
  );
  const recruitment = (history.scorecard.recruitment ?? {}) as {
    arrivals?: number;
    market_unknown_count?: number;
    valuation?: {
      fee_low_gbp?: number | null;
      fee_high_gbp?: number | null;
      counts?: Record<string, number>;
      confidence?: string;
    } | null;
  };
  const managerStints = history.staff.flatMap((person) =>
    person.stints.filter((stint) => stint.role_group === "manager"),
  );
  const selection = (history.scorecard.selection ?? {}) as {
    u21_minutes_share?: number | null;
  };
  const managerRecords = history.staff
    .flatMap((person) =>
      person.stints.flatMap((stint) =>
        stint.role_group === "manager" && stint.record
          ? [{ ...stint.record, name: person.name }]
          : [],
      ),
    )
    .sort((a, b) => String(a.start).localeCompare(String(b.start)));
  const currentStaff = history.staff
    .flatMap((person) =>
      person.stints
        .filter((stint) => !stint.end)
        .map((stint) => ({ ...stint, name: person.name })),
    )
    .filter((stint) =>
      [
        "chair",
        "manager",
        "chief_executive",
        "sporting_director",
        "assistant_manager",
        "first_team_coach",
        "goalkeeper_coach",
      ].includes(stint.role_group),
    )
    .sort((a, b) => {
      const order: Record<string, number> = {
        chair: 0,
        manager: 1,
        chief_executive: 2,
        sporting_director: 3,
        assistant_manager: 4,
        first_team_coach: 5,
        goalkeeper_coach: 6,
      };
      return (
        (order[a.role_group] ?? 99) - (order[b.role_group] ?? 99) ||
        String(a.start).localeCompare(String(b.start))
      );
    });
  const auditedFrom = history.coverage.transfer_coverage.audited_from;

  return (
    <ContractPage surface="history">
      <section className="page-head" data-contract="history.hero">
        <p className="eyebrow">The record · from 16 December 2019</p>
        <h1>{history.era.label}</h1>
        <p className="lede">
          A record of Aberdeen&apos;s strategy as well as its results:
          managers and backroom changes, recruitment, style, selection and
          silverware, with the measured record separated from the reading.
        </p>
        <div className="hero-actions">
          <span className="badge badge-neutral">
            {history.coverage.completed_seasons} completed seasons + current
          </span>
          {manifest ? (
            <span className="badge badge-neutral">
              Data as of {formatDate(manifest.generated_at.slice(0, 10))}
            </span>
          ) : null}
          <Link className="button button-ghost" href="/transfers/">
            Transfer register
          </Link>
        </div>
      </section>

      <section className="stat-row four" data-contract="history.scorecard">
        <StatTile
          label="League finishes"
          value={
            history.scorecard.best_position !== null
              ? `${history.scorecard.best_position}–${history.scorecard.worst_position}`
              : "—"
          }
          note={`${history.scorecard.seasons} completed seasons`}
        />
        <StatTile
          label="Major honours"
          value={history.scorecard.honours_total}
          note="Cormack era"
        />
        <StatTile
          label="People in charge"
          value={history.scorecard.manager_count}
          note={`including interim spells · ${managerStints.length} stints`}
        />
        <StatTile
          label="Estimated net"
          value={moneyRange(
            recruitment.valuation?.fee_low_gbp,
            recruitment.valuation?.fee_high_gbp,
          )}
          note={`inferred · ${recruitment.valuation?.confidence ?? "low"} confidence · ${
            (recruitment.valuation?.counts?.disclosed ?? 0) +
            (recruitment.valuation?.counts?.reported ?? 0)
          } known · ${recruitment.valuation?.counts?.modelled ?? 0} modelled · negative = income`}
          indicator="confidence"
        />
      </section>

      <section className="section" data-contract="history.thesis">
        <div className="section-head">
          <div>
            <p className="eyebrow">The thesis</p>
            <h2>What the record is testing</h2>
          </div>
          <span className="badge badge-warn">Curated context</span>
        </div>
        <div className="era-pillars">
          {history.era.pillars.map((pillar) => (
            <article className="pillar-card" key={pillar.id}>
              <h3>{pillar.title}</h3>
              <p>{pillar.statement}</p>
              <p className="fine-print">
                Evidence: {pillar.evidence.join(" · ")}
              </p>
              {pillar.id === "market-edge" && recruitment.arrivals ? (
                <p className="fine-print">
                  Source market unknown for{" "}
                  {recruitment.market_unknown_count ?? 0} of{" "}
                  {recruitment.arrivals} arrivals (
                  {Math.round(
                    ((recruitment.market_unknown_count ?? 0) /
                      recruitment.arrivals) *
                      100,
                  )}
                  %); the pillar is bounded by that unknown share.
                </p>
              ) : null}
            </article>
          ))}
        </div>
        <p className="fine-print">{history.era.short_description}</p>
        <p className="fine-print">
          Europe: 2023-24 Conference League group stage (third of Group G);
          2025-26 Conference League league phase (35th of 36). The season pages
          carry the cup-run detail.
        </p>
      </section>

      <section className="section" data-contract="history.season-table">
        <div className="section-head">
          <div>
            <p className="eyebrow">The record</p>
            <h2>Season by season</h2>
          </div>
          <span className="badge badge-neutral">League record joined from the club payload</span>
        </div>
        <div className="table-wrap">
          <table className="league-table compact">
            <thead>
              <tr>
                <th>Season</th>
                <th>Manager(s)</th>
                <th>League</th>
                <th className="num">Pos</th>
                <th className="num">Pts</th>
                <th>Honours</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {history.seasons.map((season) => {
                const row = clubHistory.get(season.season);
                const managers = season.manager_person_ids
                  .map((id) => names.get(id) ?? id)
                  .join(", ");
                return (
                  <tr key={season.season}>
                    <td className="strong">
                      <Link href={season.href}>{season.season}</Link>
                    </td>
                    <td>{managers || "—"}</td>
                    <td>{row ? (season.competition_name ?? "League") : "—"}</td>
                    <td className="num">{row?.position ?? "—"}</td>
                    <td className="num">{row?.points ?? "—"}</td>
                    <td>
                      {season.honour_ids.length
                        ? season.honour_ids
                            .map(
                              (id) =>
                                history.honours.find((honour) => honour.honour_id === id)
                                  ?.competition ?? id,
                            )
                            .join(", ")
                        : "—"}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          season.review_status === "complete"
                            ? "badge-ok"
                            : "badge-warn"
                        }`}
                      >
                        {seasonStatusLabel(season.status)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="fine-print">
          The league row is the measured record. Manager names and honours are
          curated; the season page holds the within-season detail.
        </p>
      </section>

      <div className="grid two-col">
        <section className="card" data-contract="history.people">
          <div className="section-head">
            <div>
              <p className="eyebrow">The people</p>
              <h2>Managers, backroom and board</h2>
            </div>
          </div>
          <ul className="plain-list current-staff">
            {currentStaff.map((stint) => (
              <li key={stint.stint_id}>
                <strong>{stint.name}</strong> · {stint.role}
                <span className="fine-print"> · since {stint.start}</span>
              </li>
            ))}
          </ul>
          <details className="timeline-details">
            <summary>
              Full staff timeline · {history.staff.length} people,{" "}
              {history.staff.reduce((sum, person) => sum + person.stints.length, 0)}{" "}
              stints
            </summary>
            <HistoryTimeline staff={history.staff} honours={history.honours} />
          </details>
          <p className="fine-print">
            Key named football-operations and board roles only. Dates keep the
            precision of the public source. Expand the timeline for every
            appointment and departure, including interim spells.
          </p>
        </section>

        <section className="card" data-contract="history.baseline">
          <div className="section-head">
            <div>
              <p className="eyebrow">Before the era</p>
              <h2>League-only baseline · chosen comparison</h2>
            </div>
            <span className="badge badge-neutral">2013-14 to 2018-19</span>
          </div>
          <p>
            {history.baseline.count ?? 0} seasons · average finish{" "}
            <strong>{history.baseline.average_position ?? "—"}</strong> · best{" "}
            <strong>{history.baseline.best_position ?? "—"}</strong> · average
            points <strong>{history.baseline.average_points ?? "—"}</strong>.
            This is the six seasons immediately before the era: a chosen
            comparison window, not a neutral norm.
          </p>
          <div className="table-wrap">
            <table className="league-table compact">
              <thead>
                <tr>
                  <th>Season</th>
                  <th className="num">Pos</th>
                  <th className="num">Pts</th>
                </tr>
              </thead>
              <tbody>
                {(history.baseline.seasons ?? []).map((row) => (
                  <tr key={String(row.season)}>
                    <td>{String(row.season)}</td>
                    <td className="num">{String(row.position ?? "—")}</td>
                    <td className="num">{String(row.points ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="fine-print">{history.baseline.note}</p>
        </section>
      </div>

      <section className="section" data-contract="history.managers">
        <div className="section-head">
          <div>
            <p className="eyebrow">The people</p>
            <h2>Manager records</h2>
          </div>
          <span className="badge badge-neutral">League only · full stint</span>
        </div>
        <ManagerRecordTable records={managerRecords} />
        <p className="fine-print">
          Full-stint league records, including interim spells. A match in a gap
          between stints is not assigned to the nearest manager. Cup and
          European results are curated exit rounds on the season pages.
        </p>
      </section>

      <section className="section" data-contract="history.honours">
        <div className="section-head">
          <div>
            <p className="eyebrow">Silverware</p>
            <h2>The cabinet</h2>
          </div>
          <span className="badge badge-neutral">{history.honours.length} major honours</span>
        </div>
        <HonoursCabinet honours={history.honours} />
        <p className="fine-print">
          The 2024-25 Scottish Cup is the Cormack-era honour. The 2023-24
          League Cup was a runners-up finish and is recorded as a cup run on
          that season page, not in the cabinet.
        </p>
      </section>

      <section className="card read-block" data-contract="history.read">
        <p className="eyebrow">The read</p>
        <h2>An assessment, not a measurement</h2>
        <p>{history.era.read}</p>
        <p className="fine-print">
          This is fitba&apos;s reading of the public record. It is not the
          club&apos;s internal view, and it is not a verdict on any individual.
        </p>
      </section>

      <section className="section" data-contract="history.coverage">
        <div className="section-head">
          <div>
            <p className="eyebrow">What is covered</p>
            <h2>Coverage by season</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table className="league-table compact">
            <thead>
              <tr>
                <th>Season</th>
                <th>League</th>
                <th>Transfers</th>
                <th>Lineups</th>
                <th>Match stats</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {history.seasons.map((season) => {
                const backfill = history.coverage.backfill[season.season];
                const transfers =
                  season.season >= auditedFrom ? "Audited" : "Curated partial";
                return (
                  <tr key={`coverage-${season.season}`}>
                    <td>{season.season}</td>
                    <td>Measured</td>
                    <td>{transfers}</td>
                    <td>
                      {backfill
                        ? `${backfill.status} · ${backfill.fixtures_with_lineups}/${backfill.fixtures_total}`
                        : "Unavailable"}
                    </td>
                    <td>Measured proxies</td>
                    <td>{season.review_status === "complete" ? "Complete" : "In progress"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="fine-print">{history.coverage.note}</p>
        <p className="fine-print">
          Selection averages for the era cover{" "}
          {String(selection.u21_minutes_share ?? "—")} U21 minutes share where
          the lineup backfill is available. Manager records are league-only.
        </p>
        <p className="back-link" data-contract-indicator="source">
          <Link href="/sources/">Sources</Link>
          {" · "}
          <Link href="/methodology/">Method</Link>
          {" · "}
          <Link href="/transfers/">Transfer register</Link>
        </p>
      </section>
    </ContractPage>
  );
}
