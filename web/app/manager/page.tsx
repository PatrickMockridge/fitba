import Link from "next/link";
import { AsOfBadge } from "@/components/AsOfBadge";
import { ContractPage } from "@/components/ContractPage";
import { ManagerRecordTable } from "@/components/ManagerRecordTable";
import { ManagerXgTable } from "@/components/ManagerXgTable";
import { StatTile } from "@/components/StatTile";
import { formatDate, formatDecimal, formatSigned } from "@/lib/format";
import {
  getAberdeen,
  getAnalysisSummary,
  getDonstalkSignal,
  getHistory,
  getHistorySeason,
  getManifest,
  getXg,
  type HistoryManagerRecord,
} from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/manager/" },
  title: "Manager record · fitba",
  description:
    "Aberdeen's manager record: the current permanent, interim or vacancy situation, analyst-set season expectations, the measured manager record, manager churn in the Cormack era, and links to manager news and rumours.",
};

function ordinal(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const suffix =
    value % 10 === 1 && value % 100 !== 11
      ? "st"
      : value % 10 === 2 && value % 100 !== 12
        ? "nd"
        : value % 10 === 3 && value % 100 !== 13
          ? "rd"
          : "th";
  return `${value}${suffix}`;
}

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function reasonLabel(value: string | null | undefined): string {
  if (!value) return "In post";
  if (value === "dismissed") return "Dismissed";
  if (value === "resigned") return "Resigned";
  if (value === "interim_end") return "Interim ended";
  return value.replaceAll("_", " ");
}

function departureVerb(value: string | null | undefined): string {
  if (value === "dismissed") return "was dismissed";
  if (value === "resigned") return "resigned";
  return "left the post";
}

export default function ManagerPage() {
  const history = getHistory();
  const analysis = getAnalysisSummary();
  const xg = getXg();
  const aberdeen = getAberdeen();
  const donstalk = getDonstalkSignal();
  const manifest = getManifest();

  if (!history) {
    return (
      <ContractPage surface="manager" state="empty">
        <section className="empty-state" data-contract="manager.empty">
          <h1>No manager record published</h1>
          <p>
            Run <code>uv run fitba publish</code> after curating the history
            register.
          </p>
        </section>
      </ContractPage>
    );
  }

  const seasonRef =
    history.seasons.find((row) => row.status === "in_progress") ??
    history.seasons[history.seasons.length - 1] ??
    null;
  const season = analysis?.season ?? seasonRef?.season ?? null;
  const seasonDoc = season ? getHistorySeason(season) : null;
  const expectations = (seasonDoc?.expectations ?? {}) as Record<string, unknown>;
  const expectationSources = Array.isArray(expectations.source_urls)
    ? expectations.source_urls.filter(
        (value): value is string => typeof value === "string",
      )
    : [];
  const clubStatementUrl = expectationSources.find((url) =>
    url.includes("afc.co.uk"),
  );
  const managerStints = history.staff
    .flatMap((person) =>
      person.stints
        .filter((stint) => stint.role_group === "manager")
        .map((stint) => ({
          ...stint,
          name: person.name,
          person_id: person.person_id,
        })),
    )
    .sort((left, right) => String(left.start).localeCompare(String(right.start)));
  const currentManagers = managerStints.filter((stint) => !stint.end);
  const currentPermanent = currentManagers.find((stint) => !stint.interim);
  const currentInterim = currentManagers.find((stint) => stint.interim);
  const lastPermanent = managerStints
    .filter((stint) => !stint.interim && stint.end)
    .sort((left, right) => String(right.end).localeCompare(String(left.end)))[0];
  const eraStints = managerStints.filter(
    (stint) => !stint.end || String(stint.end) >= history.era.start,
  );
  const seasonManagerIds = new Set(
    (seasonDoc?.managers ?? []).map((row) => row.person_id),
  );
  const currentManagerRecords = managerStints
    .filter(
      (stint) => seasonManagerIds.has(stint.person_id) && stint.record,
    )
    .map((stint) => stint.record as HistoryManagerRecord)
    .sort((left, right) => String(left.start).localeCompare(String(right.start)));
  const seasonManagerRecords = (seasonDoc?.managers ?? []).map(
    (row) => row as HistoryManagerRecord,
  );
  const xgRows = (xg?.manager_splits ?? []).filter(
    (row) => !season || row.season === season,
  );
  const managerNames = history.staff
    .filter((person) =>
      person.stints.some((stint) => stint.role_group === "manager"),
    )
    .map((person) => person.name);
  const managerNews = (aberdeen?.news ?? [])
    .filter((article) => {
      const title = article.title.toLocaleLowerCase("en-GB");
      return (
        managerNames.some((name) =>
          title.includes(name.toLocaleLowerCase("en-GB")),
        ) ||
        title.includes("manager") ||
        title.includes("head coach")
      );
    })
    .sort((left, right) =>
      String(right.published_date ?? "").localeCompare(
        String(left.published_date ?? ""),
      ),
    )
    .slice(0, 5);
  const nextManagerThread = donstalk?.topics.find(
    (topic) => topic.title.trim().toLocaleLowerCase("en-GB") === "next manager",
  );
  const hero = analysis?.hero;
  const currentSeasonAim = analysis?.aims.find((aim) => aim.id === "league");
  const nextFixture = analysis?.next_up?.[0] ?? null;

  return (
    <ContractPage surface="manager">
      <section className="page-head" data-contract="manager.hero">
        <p className="eyebrow">{season ? `Season ${season} · Manager record` : "Manager record"}</p>
        <h1>The manager record</h1>
        <p className="lede">
          {currentPermanent
            ? `${currentPermanent.name} is the permanent manager${
                currentPermanent.start
                  ? `, appointed ${formatDate(currentPermanent.start)}`
                  : ""
              }.`
            : `No permanent manager.${
                currentInterim
                  ? ` ${currentInterim.name} is interim${
                      currentInterim.start
                        ? ` since ${formatDate(currentInterim.start)}`
                        : ""
                    }.`
                  : ""
              }`}{" "}
          {lastPermanent
            ? `${lastPermanent.name} ${departureVerb(lastPermanent.reason_out)}${
                lastPermanent.end ? ` on ${formatDate(lastPermanent.end)}` : ""
              } after ${lastPermanent.record?.played ?? 0} league matches.`
            : ""}
        </p>
        <div className="hero-actions">
          <span className="badge badge-warn">
            {currentPermanent ? "Permanent manager" : "Vacancy"}
          </span>
          {currentInterim ? (
            <span className="badge badge-neutral">Interim in charge</span>
          ) : null}
          <span className="badge badge-neutral">League-only manager records</span>
          <AsOfBadge generatedAt={history.generated_at} />
        </div>
      </section>

      <section className="stat-row four" data-contract="manager.situation">
        <StatTile
          label="Manager"
          value={currentPermanent?.name ?? "Vacancy"}
          note={
            currentInterim
              ? `${currentInterim.name} interim${
                  currentInterim.start
                    ? ` since ${formatDate(currentInterim.start)}`
                    : ""
                }`
              : currentPermanent?.start
                ? `Since ${formatDate(currentPermanent.start)}`
                : "No current manager in the staff register"
          }
        />
        <StatTile
          label="League position"
          value={ordinal(hero?.position)}
          note={
            hero
              ? `${hero.points ?? "—"} pts after ${hero.played ?? "—"} · GD ${
                  hero.goal_difference === null ||
                  hero.goal_difference === undefined
                    ? "—"
                    : formatSigned(hero.goal_difference, 0)
                }`
              : "League record unavailable"
          }
        />
        <StatTile
          label="Last permanent manager"
          value={lastPermanent?.name ?? "—"}
          note={
            lastPermanent
              ? `${lastPermanent.end ? formatDate(lastPermanent.end) : "—"} · ${
                  lastPermanent.record?.played ?? 0
                } league matches · ${
                  lastPermanent.record?.ppg === null ||
                  lastPermanent.record?.ppg === undefined
                    ? "—"
                    : formatDecimal(lastPermanent.record.ppg)
                } PPG`
              : "No completed permanent stint published"
          }
        />
        <StatTile
          label="Next fixture"
          value={
            nextFixture ? (
              <Link href="/matchday/">{nextFixture.opponent_name}</Link>
            ) : (
              "—"
            )
          }
          note={
            nextFixture
              ? `${formatDate(nextFixture.date)} · ${
                  nextFixture.venue === "H"
                    ? "Home"
                    : nextFixture.venue === "A"
                      ? "Away"
                      : "Neutral"
                } · ${nextFixture.kickoff ?? "TBC"}`
              : "No scheduled fixture published"
          }
        />
      </section>
      <p className="fine-print">
        {currentSeasonAim
          ? `${currentSeasonAim.label}: ${currentSeasonAim.current}. `
          : ""}
        {clubStatementUrl ? (
          <a className="text-link" href={clubStatementUrl}>
            Club statement
          </a>
        ) : (
          <Link className="text-link" href="/news/">
            Club news
          </Link>
        )}
        {" · "}
        <Link className="text-link" href="/history/">
          The full manager register
        </Link>
      </p>

      <section className="section" data-contract="manager.expectations">
        <div className="section-head">
          <div>
            <p className="eyebrow">Season expectations</p>
            <h2>What this season is for</h2>
          </div>
          <span
            className="badge badge-neutral"
            data-contract-indicator="confidence"
          >
            Analyst-set, not a published club target
          </span>
        </div>
        {expectations.baseline || expectations.target || expectations.context ? (
          <div className="grid two-col">
            <div>
              <h3>Baseline</h3>
              <p>{text(expectations.baseline) || "—"}</p>
              <h3>Target</h3>
              <p>{text(expectations.target) || "—"}</p>
            </div>
            <div>
              <h3>Context</h3>
              <p>{text(expectations.context) || "—"}</p>
              <p className="fine-print" data-contract-indicator="source">
                {expectationSources.length ? (
                  <>
                    Sources:{" "}
                    {expectationSources.map((url, index) => (
                      <span key={url}>
                        {index ? " · " : ""}
                        <a className="text-link" href={url}>
                          {url.includes("afc.co.uk") ? "Club statement" : "Wikipedia"}
                        </a>
                      </span>
                    ))}
                  </>
                ) : (
                  "No source URL published for the season expectations."
                )}
              </p>
            </div>
          </div>
        ) : (
          <p className="fine-print">
            No season expectations are published for {season ?? "this season"}.
          </p>
        )}
        <p className="fine-print">
          The baseline is the measured starting point; the target is an
          analyst-set reading, not a club target and not a per-manager target.
        </p>
      </section>

      <section className="section" data-contract="manager.aims">
        <div className="section-head">
          <div>
            <p className="eyebrow">Season aims</p>
            <h2>The three season aims</h2>
          </div>
          <span className="badge badge-neutral">Analyst-set aims</span>
        </div>
        {analysis?.aims.length ? (
          <div className="table-wrap">
            <table className="league-table compact">
              <caption className="fine-print">
                Analyst-set aims from the season overview. The gap is the
                published distance; unknown is not zero.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Aim</th>
                  <th scope="col">Target</th>
                  <th scope="col">Current</th>
                  <th scope="col">Status</th>
                  <th scope="col">Gap</th>
                </tr>
              </thead>
              <tbody>
                {analysis.aims.map((aim) => (
                  <tr key={aim.id}>
                    <td>{aim.label}</td>
                    <td>{aim.target}</td>
                    <td>{aim.current}</td>
                    <td>
                      {aim.status === "unknown" ? (
                        <span className="badge badge-neutral">Unknown</span>
                      ) : (
                        aim.status.replaceAll("_", " ")
                      )}
                    </td>
                    <td className="num">{aim.gap ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="fine-print">No season aims are published.</p>
        )}
      </section>

      <section className="section" data-contract="manager.record">
        <div className="section-head">
          <div>
            <p className="eyebrow">The measured record</p>
            <h2>The measured manager record</h2>
          </div>
          <span className="badge badge-neutral">League only · full stint</span>
        </div>
        <ManagerRecordTable
          records={currentManagerRecords}
          caption="Full-stint league records for the managers in the current season. League only; interim spells are separate."
          empty="No full-stint manager record is published for the current season."
        />
        <p className="fine-print" data-contract-indicator="basis">
          Measured context, not a manager rating. No per-manager target or
          causal verdict is published. The full-stint record covers every league
          match in the stint, not only this season.
        </p>
        <p className="fine-print" data-contract-indicator="unknown">
          A manager stint with no league match is a zero sample, not a
          zero-performance verdict. Zero matches is not the same as zero points
          per game.
        </p>
      </section>

      <section className="section" data-contract="manager.season-record">
        <div className="section-head">
          <div>
            <p className="eyebrow">This season</p>
            <h2>The {season ?? "current"} league segment</h2>
          </div>
          <span className="badge badge-neutral">Within-season segment</span>
        </div>
        <ManagerRecordTable
          records={seasonManagerRecords}
          caption="The within-season league segment, not the full stint. League only; interim spells are separate."
          empty="No manager segment is published for this season."
        />
        <p className="fine-print">
          A within-season segment can differ from the full-stint record: the
          full stint includes league matches from any earlier season. The season
          document is the source of both scopes.
        </p>
      </section>

      <section className="section" data-contract="manager.xg">
        <div className="section-head">
          <div>
            <p className="eyebrow">fxG context</p>
            <h2>Manager league spells compared</h2>
          </div>
          <span className="badge badge-neutral">Descriptive</span>
        </div>
        {xgRows.length ? (
          <ManagerXgTable rows={xgRows} compact />
        ) : (
          <p className="fine-print" data-contract-indicator="unknown">
            No manager xG split is published for {season ?? "this season"}. The
            absence is unknown, not zero.
          </p>
        )}
        <p className="fine-print">
          fxG is fitba&apos;s open-play shot-zone model, not provider xG. The
          split is descriptive, not a causal verdict on a manager.
        </p>
        <p className="back-link">
          <Link href="/analysis/xg/">Full fxG manager split →</Link>
        </p>
      </section>

      <section className="section" data-contract="manager.churn">
        <div className="section-head">
          <div>
            <p className="eyebrow">The Cormack era</p>
            <h2>Manager churn, stint by stint</h2>
          </div>
          <span className="badge badge-neutral">
            {history.scorecard.manager_count} people with a league match ·{" "}
            {eraStints.length} manager stints
          </span>
        </div>
        <div className="table-wrap">
          <table className="league-table compact">
            <caption className="fine-print">
              Every manager stint overlapping the Cormack era from{" "}
              {formatDate(history.era.start)}. League only. A match in a gap
              between stints is not assigned to the nearest manager; cup and
              European results are not in these records.
            </caption>
            <thead>
              <tr>
                <th scope="col">Manager</th>
                <th scope="col">Dates</th>
                <th scope="col">Reason</th>
                <th scope="col" className="num">
                  Pld
                </th>
                <th scope="col">W-D-L</th>
                <th scope="col" className="num">
                  GF
                </th>
                <th scope="col" className="num">
                  GA
                </th>
                <th scope="col" className="num">
                  Pts
                </th>
                <th scope="col" className="num">
                  PPG
                </th>
              </tr>
            </thead>
            <tbody>
              {eraStints.map((stint) => {
                const record = stint.record;
                return (
                  <tr key={stint.stint_id}>
                    <td>
                      {stint.name}
                      {stint.interim ? (
                        <span className="badge badge-warn"> Interim</span>
                      ) : null}
                      {stint.start < history.era.start ? (
                        <span className="badge badge-neutral"> Pre-era start</span>
                      ) : null}
                    </td>
                    <td className="fine-print">
                      {formatDate(stint.start)} –{" "}
                      {stint.end ? formatDate(stint.end) : "present"}
                    </td>
                    <td>{reasonLabel(stint.reason_out)}</td>
                    <td className="num">{record?.played ?? 0}</td>
                    <td>
                      {record
                        ? `${record.won}-${record.drawn}-${record.lost}`
                        : "—"}
                    </td>
                    <td className="num">{record?.gf ?? 0}</td>
                    <td className="num">{record?.ga ?? 0}</td>
                    <td className="num strong">{record?.points ?? 0}</td>
                    <td className="num">
                      {record?.ppg === null || record?.ppg === undefined
                        ? "—"
                        : formatDecimal(record.ppg)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="fine-print">
          The manager count counts distinct people with at least one league
          match; the table also shows zero-match stints such as a current
          interim. <Link href="/history/">The full staff timeline and records</Link>{" "}
          include the board and backroom.
        </p>
      </section>

      <section className="section" data-contract="manager.news">
        <div className="section-head">
          <div>
            <p className="eyebrow">The news</p>
            <h2>Manager headlines</h2>
          </div>
          <span className="badge badge-neutral">Listing metadata only</span>
        </div>
        <p className="fine-print">
          AFC news items whose title names a published manager, the manager or
          the head coach. Newest first; article bodies are not copied.
        </p>
        {managerNews.length ? (
          <ul className="plain-list">
            {managerNews.map((article) => (
              <li key={article.article_id}>
                <a className="text-link" href={article.url}>
                  {article.title}
                </a>
                <span className="fine-print">
                  {" "}
                  · {article.published_date ? formatDate(article.published_date) : "Date unknown"}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="fine-print">
            No manager headline is published in the current AFC news feed.
          </p>
        )}
        <p className="back-link">
          <Link href="/news/">All AFC news →</Link>
          {clubStatementUrl ? (
            <>
              {" · "}
              <a className="text-link" href={clubStatementUrl}>
                Club statement
              </a>
            </>
          ) : null}
        </p>
      </section>

      <section className="section" data-contract="manager.rumours">
        <div className="section-head">
          <div>
            <p className="eyebrow">The signal</p>
            <h2>Next manager and fan signal</h2>
          </div>
          <span className="badge badge-neutral">Link only</span>
        </div>
        <p>
          The next-manager market, the fan-signal panels and the coverage notes
          live on the rumour mill. Odds, if published, are on the rumour mill and
          are not betting advice. No odds table is duplicated here.
        </p>
        <p className="back-link">
          <Link href="/rumours/">Next-manager market and fan signal →</Link>
          {nextManagerThread ? (
            <>
              {" · "}
              <a className="text-link" href={nextManagerThread.url}>
                DonsTalk: Next manager
              </a>
            </>
          ) : null}
        </p>
        <p className="fine-print" data-contract-indicator="source">
          The manager market is a single public bookmaker snapshot, published
          only while Aberdeen have no permanent manager. It is not a
          probability, a recommendation or a promotion, and fitba has no
          affiliate or advertising relationship.
        </p>
      </section>

      <section className="section" data-contract="manager.coverage">
        <div className="section-head">
          <div>
            <p className="eyebrow">What is covered</p>
            <h2>Coverage and method</h2>
          </div>
        </div>
        <ul className="plain-list">
          <li>
            Manager records are league-only. Cup and European results are
            curated exit rounds on the season pages.
          </li>
          <li>
            The manager count counts people with at least one league match. An
            interim with no match is a zero sample, not a zero-performance
            verdict.
          </li>
          <li>Season expectations are analyst-set, not club targets.</li>
          <li>
            fxG is descriptive and not a causal verdict; provider xG and fitba
            fxG are separate models.
          </li>
          <li>
            News rows are listing metadata. The next-manager market is gated and
            lives on the rumour mill.
          </li>
          <li>
            The page does not publish a manager rating, a per-manager target or
            a causal judgement.
          </li>
        </ul>
        <p className="fine-print" data-contract-indicator="source">
          Sources: the curated history register, the current season document,
          the season overview, the fxG document, the AFC news feed and the
          published staff register.
        </p>
        <p className="back-link">
          <Link href="/history/">The Cormack era</Link>
          {" · "}
          {season ? (
            <>
              <Link href={seasonRef?.href ?? `/history/${season}/`}>
                {season} season
              </Link>
              {" · "}
            </>
          ) : null}
          <Link href="/analysis/">Season overview</Link>
          {" · "}
          <Link href="/analysis/xg/">fxG analysis</Link>
          {" · "}
          <Link href="/rumours/">Rumour mill</Link>
          {" · "}
          <Link href="/news/">News</Link>
          {" · "}
          <Link href="/claims/">Claims</Link>
          {" · "}
          <Link href="/methodology/">Method</Link>
          {" · "}
          <Link href="/sources/">Sources</Link>
        </p>
        <p className="fine-print">
          {manifest
            ? `Published corpus generated ${formatDate(manifest.generated_at)}.`
            : "Publication timestamp unavailable."}
        </p>
      </section>
    </ContractPage>
  );
}
