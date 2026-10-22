import Link from "next/link";
import { FormStrip } from "@/components/FormStrip";
import { LegendDisclosure } from "@/components/LegendDisclosure";
import { MetricStrip } from "@/components/MetricStrip";
import { PageHeader } from "@/components/PageHeader";
import { TableFrame, Th } from "@/components/TableFrame";
import { formatDate, plainText } from "@/lib/format";
import {
  getAberdeen,
  getManifest,
  getRumours,
  getSquad,
  getTableFiles,
  getThemes,
  getTransfers,
} from "@/lib/data";

export default function HomePage() {
  const manifest = getManifest();
  const tables = getTableFiles();
  const aberdeen = getAberdeen();
  const transfers = getTransfers();
  const rumours = getRumours();
  const squad = getSquad();
  const themes = getThemes();
  const season = manifest?.season ?? tables[0]?.season ?? "—";

  if (!tables.length) {
    return (
      <section className="page-head">
        <h1>No data published yet</h1>
        <p className="page-summary">
          The current-season tables have not been published. Check the{" "}
          <Link className="text-link" href="/status/">
            data status
          </Link>{" "}
          page.
        </p>
      </section>
    );
  }

  const aberdeenTable = tables.find((table) =>
    table.rows.some((row) => row.team_id === "sco:aberdeen"),
  );
  const summary = aberdeen?.summary;
  const nextFixture = aberdeen?.fixtures?.[0];
  const aberdeenRow = aberdeenTable?.rows.find((row) => row.team_id === "sco:aberdeen");
  const rowIndex = aberdeenTable?.rows.findIndex((row) => row.team_id === "sco:aberdeen") ?? -1;
  const competitionSlug = aberdeenTable?.competition_id.split(":").pop() ?? "premiership";
  const tableSlice =
    rowIndex >= 0 && aberdeenTable
      ? aberdeenTable.rows.slice(Math.max(0, rowIndex - 1), Math.min(aberdeenTable.rows.length, rowIndex + 2))
      : [];
  const themeLine = themes?.themes.find((theme) => theme.horizon === "season")?.headline;
  const latestArticle = aberdeen?.news?.[0];

  const summaryLine =
    summary && aberdeenRow
      ? `${summary.position}th in the ${aberdeenTable?.short_name ?? "league"} on ${summary.points} points.${
          nextFixture
            ? ` Next: ${nextFixture.opponent_name} ${nextFixture.venue === "A" ? "away" : "home"}, ${formatDate(nextFixture.date)}${nextFixture.kickoff ? `, ${nextFixture.kickoff}` : ""}.`
            : ""
        }`
      : "Aberdeen's season at a glance.";

  return (
    <>
      <PageHeader
        eyebrow={`Season ${season}`}
        title="Aberdeen, this week."
        summary={summaryLine}
        actions={
          <>
            <Link className="button" href="/matchday/">
              Matchday
            </Link>
            <Link className="button button-ghost" href="/squad/">
              Squad
            </Link>
            <Link className="button button-ghost" href="/recruitment/">
              Off the pitch
            </Link>
          </>
        }
      />

      <MetricStrip
        columns={4}
        items={[
          {
            label: "Position",
            value: summary?.position ?? "—",
            note: aberdeenTable?.short_name ?? "League",
          },
          {
            label: "Points",
            value: summary?.points ?? "—",
            note: `${summary?.played ?? "—"} played`,
          },
          {
            label: "Form",
            value: summary?.form ? <FormStrip form={summary.form} /> : "—",
            note: "Last five",
          },
          {
            label: "Next",
            value: nextFixture ? (nextFixture.venue === "A" ? "Away" : "Home") : "—",
            note: nextFixture?.opponent_name ?? "No fixture",
          },
        ]}
      />

      <section className="grid three-col">
        <article className="card">
          <p className="eyebrow">Matchday</p>
          <h2>Who is next?</h2>
          <p className="muted">
            {nextFixture
              ? `${nextFixture.opponent_name} ${nextFixture.venue === "A" ? "away" : "home"} · ${formatDate(nextFixture.date)}`
              : "No upcoming fixture."}
          </p>
          <Link className="text-link" href="/matchday/">
            Predicted XIs and form →
          </Link>
        </article>

        <article className="card">
          <p className="eyebrow">Squad</p>
          <h2>Who is available?</h2>
          <p className="muted">
            {squad
              ? `${squad.summary.squad_size} registered · ${squad.summary.loans_out} out on loan · average age ${squad.summary.average_age ?? "—"}`
              : "Squad data unavailable."}
          </p>
          <Link className="text-link" href="/squad/">
            Squad and loans →
          </Link>
        </article>

        <article className="card">
          <p className="eyebrow">Off the pitch</p>
          <h2>What changed?</h2>
          <p className="muted">
            {transfers
              ? `${transfers.summary.total} moves · ${transfers.summary.period ?? "register"} · ${transfers.summary.confirmed} officially confirmed · ${rumours?.summary.by_status.active ?? 0} active rumours`
              : "Transfer register unavailable."}
          </p>
          <Link className="text-link" href="/transfers/">
            Transfers and loans →
          </Link>
        </article>
      </section>

      {aberdeenTable && tableSlice.length ? (
        <section className="section">
          <div className="section-head">
            <div>
              <p className="eyebrow">{aberdeenTable.short_name}</p>
              <h2>Around Aberdeen</h2>
            </div>
            <Link className="text-link" href={`/scotland/${competitionSlug}/`}>
              Full table →
            </Link>
          </div>
          <TableFrame
            label="Premiership table around Aberdeen"
            caption="Scottish Premiership standings around Aberdeen"
          >
            <thead>
              <tr>
                <Th className="num">#</Th>
                <Th>Club</Th>
                <Th className="num">P</Th>
                <Th className="num">Pts</Th>
                <Th className="num">GD</Th>
              </tr>
            </thead>
            <tbody>
              {tableSlice.map((row) => (
                <tr
                  key={row.team_id}
                  className={row.team_id === "sco:aberdeen" ? "is-highlight" : undefined}
                >
                  <td className="num">{row.position}</td>
                  <td>{row.team_name}</td>
                  <td className="num">{row.played}</td>
                  <td className="num strong">{row.points}</td>
                  <td className="num">{row.gd > 0 ? `+${row.gd}` : row.gd}</td>
                </tr>
              ))}
            </tbody>
          </TableFrame>
        </section>
      ) : null}

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">The bigger picture</p>
            <h2>What is the trend?</h2>
          </div>
          <Link className="text-link" href="/themes/">
            Themes →
          </Link>
        </div>
        <p className="page-summary">
          {themeLine
            ? plainText(themeLine)
            : "The current-season themes are published on the themes page."}
        </p>
      </section>

      {latestArticle ? (
        <section className="section">
          <div className="section-head">
            <div>
              <p className="eyebrow">From Pittodrie</p>
              <h2>Latest news</h2>
            </div>
            <Link className="text-link" href="/news/">
              All news →
            </Link>
          </div>
          <p className="page-summary">
            <a href={latestArticle.url} target="_blank" rel="noreferrer">
              {latestArticle.title}
            </a>
            {latestArticle.published_date ? ` · ${formatDate(latestArticle.published_date)}` : ""}
          </p>
        </section>
      ) : null}

      <LegendDisclosure>
        <p>
          League position and form come from the current-season table. The squad
          count and transfer register are published independently and update on
          the daily publish. Player names link to their profiles.
        </p>
        <p>
          Full method: <Link href="/methodology/">methodology</Link> ·{" "}
          <Link href="/sources/">sources</Link> · <Link href="/status/">data status</Link>.
        </p>
      </LegendDisclosure>
    </>
  );
}
