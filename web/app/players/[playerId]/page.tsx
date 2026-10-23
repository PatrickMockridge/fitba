import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ContractPage } from "@/components/ContractPage";
import { Panel } from "@/components/Panel";
import { PlayerRose } from "@/components/PlayerRose";
import { ProfileHeader } from "@/components/ProfileHeader";
import { ProfileSection } from "@/components/ProfileSection";
import { RoleInferenceContent } from "@/components/RoleInference";
import { StatTile } from "@/components/StatTile";
import { formatDate, formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";
import { getPlayerPage, getSquad } from "@/lib/data";
import type { SquadStat } from "@/lib/data";
import type {
  AvailabilityPanelData,
  IdentityBlock,
  PerformancePanel,
  PlayerPageDocument,
  RecentMatch,
  TableColumn,
} from "@/lib/player-page";

export const dynamicParams = false;

export function generateStaticParams() {
  const squad = getSquad();
  return (squad?.players ?? []).map((player) => ({ playerId: String(player.player_id) }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ playerId: string }>;
}): Promise<Metadata> {
  const { playerId } = await params;
  const page = getPlayerPage(playerId);
  const name = page?.identity.full_name || page?.identity.name;
  const title = name ? `${name} · player profile · fitba` : "Player profile · fitba";
  const description = name
    ? `${name}: statistical profile, role evidence, competitive minutes, current-season output, availability and recent matches.`
    : "Aberdeen player profile.";
  return {
    title,
    description,
    alternates: { canonical: `/players/${playerId}/` },
    openGraph: { title, description, type: "profile" },
    twitter: { card: "summary", title, description },
  };
}

function sideLabel(side: string | null): string | null {
  if (side === "left") return "Left-sided";
  if (side === "right") return "Right-sided";
  if (side === "central" || side === "centre") return "Central";
  return null;
}

function footLabel(value: string | null): string | null {
  if (value === "left") return "Left foot";
  if (value === "right") return "Right foot";
  if (value === "both") return "Both feet";
  return null;
}

function statusText(identity: IdentityBlock): string {
  if (identity.status === "loan_out") {
    return `On loan at ${identity.loan?.club ?? "an unknown club"}`;
  }
  if (identity.status === "loan_in") {
    return `On loan from ${identity.loan?.club ?? "an unknown club"}`;
  }
  return "Aberdeen squad";
}

function statusClass(status: string): string {
  return status === "squad" ? "badge badge-ok" : "badge badge-warn";
}

function formatCell(value: unknown, format?: TableColumn["format"]): string {
  if (value === null || value === undefined || value === "") return "—";
  if (format === "decimal" && typeof value === "number") return value.toFixed(2);
  if (format === "percent" && typeof value === "number") return `${Math.round(value)}%`;
  return String(value);
}

function PerformanceTable({
  columns,
  rows,
}: {
  columns: TableColumn[];
  rows: SquadStat[];
}) {
  return (
    <div className="table-wrap">
      <table className="league-table compact">
<caption className="fine-print">Player record: competition, role or defensive context.</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={column.key === "competition" || column.key === "team_name" ? undefined : "num"}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.competition}-${row.team_name}`}>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={column.key === "competition" || column.key === "team_name" ? undefined : "num"}
                >
                  {formatCell((row as unknown as Record<string, unknown>)[column.key], column.format)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlayingTimeView({ data }: { data: NonNullable<PlayerPageDocument["panels"]["playing_time"]["data"]> }) {
  const time = data.playing_time;
  return (
    <>
      <div className="stat-row four">
        <StatTile label="Starts" value={time.starts} note="lineup" />
        <StatTile label="Sub apps" value={time.sub_apps} note="entered" />
        <StatTile label="Mins started" value={time.minutes_started} note="on pitch" />
        <StatTile label="Mins as sub" value={time.minutes_as_sub} note="on pitch" />
      </div>
      <div className="table-wrap">
        <table className="league-table compact">
<caption className="fine-print">Player record: competition, role or defensive context.</caption>
          <thead>
            <tr>
              <th>Competition</th>
              <th className="num">Starts</th>
              <th className="num">Sub</th>
              <th className="num">Mins</th>
              <th className="num">Mins started</th>
              <th className="num">Mins as sub</th>
            </tr>
          </thead>
          <tbody>
            {time.by_competition.map((row) => (
              <tr key={row.competition}>
                <td>{row.competition}</td>
                <td className="num">{row.starts}</td>
                <td className="num">{row.sub_apps}</td>
                <td className="num">{row.minutes}</td>
                <td className="num">{row.minutes_started}</td>
                <td className="num">{row.minutes_as_sub}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function PerformanceView({ data }: { data: PerformancePanel }) {
  return (
    <>
      {data.tiles.length ? (
        <div className="stat-row four">
          {data.tiles.map((tile) => (
            <StatTile
              key={tile.key}
              label={tile.label}
              value={tile.value ?? "—"}
              note={tile.note}
            />
          ))}
        </div>
      ) : null}

      <div className="table-wrap">
        <table className="league-table compact">
<caption className="fine-print">Player record: competition, role or defensive context.</caption>
          <thead>
            <tr>
              {data.provider_columns.map((column) => (
                <th
                  key={column.key}
                  className={column.key === "competition" || column.key === "team_name" ? undefined : "num"}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.stats.map((row) => (
              <tr key={`${row.competition}-${row.team_name}`}>
                {data.provider_columns.map((column) => (
                  <td
                    key={column.key}
                    className={column.key === "competition" || column.key === "team_name" ? undefined : "num"}
                  >
                    {formatCell((row as unknown as Record<string, unknown>)[column.key], column.format)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.detail_columns.length ? (
        <>
          <p className="table-caption">Detail</p>
          <PerformanceTable
            columns={data.detail_columns}
            rows={data.stats}
          />
        </>
      ) : null}

      {data.position_stats.length ? (
        <>
          <p className="table-caption">Defensive context</p>
          <div className="table-wrap">
            <table className="league-table compact">
<caption className="fine-print">Player record: competition, role or defensive context.</caption>
              <thead>
                <tr>
                  <th>Competition</th>
                  <th className="num">Matches</th>
                  <th className="num">Mins on pitch</th>
                  <th className="num">Conc</th>
                  <th className="num">CS</th>
                  <th className="num">OG</th>
                </tr>
              </thead>
              <tbody>
                {data.position_stats.map((row) => (
                  <tr key={`position-${row.competition}`}>
                    <td>{row.competition}</td>
                    <td className="num">{row.matches}</td>
                    <td className="num">{row.minutes_on_pitch}</td>
                    <td className="num">{row.conceded_on_pitch}</td>
                    <td className="num">{row.clean_sheets}</td>
                    <td className="num">{row.own_goals}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </>
  );
}

const RECORD_COLUMNS: TableColumn[] = [
  { key: "competition", label: "Competition" },
  { key: "team_name", label: "Team" },
  { key: "appearances", label: "Apps" },
  { key: "starts", label: "Starts" },
  { key: "minutes", label: "Mins" },
  { key: "goals", label: "G" },
  { key: "assists", label: "A" },
  { key: "yellow_cards", label: "YC" },
  { key: "red_cards", label: "RC" },
  { key: "rating", label: "Rating", format: "decimal" },
];

function KeyFacts({ page }: { page: PlayerPageDocument }) {
  const summary = page.panels.profile.data?.summary;
  if (!summary) return null;
  return (
    <div className="stat-row four">
      <StatTile label="League minutes" value={summary.minutes} note="Premiership" />
      <StatTile
        label="Appearances"
        value={summary.appearances ?? "—"}
        note="Premiership"
      />
      <StatTile
        label="Provider rating"
        value={summary.rating === null ? "—" : formatDecimal(summary.rating)}
        note="opaque; not a verdict"
      />
      <StatTile
        label="Cohort percentile"
        value={
          summary.rating_percentile === null
            ? "—"
            : formatPercentValue(summary.rating_percentile, 1)
        }
        note={
          summary.cohort_n
            ? `${summary.cohort_basis ?? "role"} cohort, n=${summary.cohort_n}`
            : "cohort unavailable"
        }
      />
    </div>
  );
}

function AvailabilityView({ data }: { data: AvailabilityPanelData }) {
  const availability = data.availability;
  return (
    <div>
      <div className="stat-row four">
        <StatTile label="Status" value={availability.status} note={availability.confidence} />
        <StatTile label="Reason" value={availability.reason ?? "—"} note={availability.reason_category ?? ""} />
        <StatTile
          label="Expected return"
          value={availability.expected_return ?? "—"}
          note="official team news only"
        />
        <StatTile
          label="Verified"
          value={
            availability.verified_at ? formatDate(availability.verified_at) : "—"
          }
          note={availability.source_id ?? "no source"}
        />
      </div>
      <p className="fine-print">
        {availability.note ?? "No verified official team-news entry."}
        {availability.source_url ? (
          <>
            {" "}
            <a href={availability.source_url} target="_blank" rel="noreferrer">
              Source
            </a>
          </>
        ) : null}
      </p>
    </div>
  );
}

function RecentMatchesView({ rows }: { rows: RecentMatch[] }) {
  if (!rows.length) {
    return <p className="muted">No current-season competitive match rows are available.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="league-table compact">
        <caption className="fine-print">
          Latest 10 competitive current-season rows. Missing provider values are a dash, not zero.
        </caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Competition</th>
            <th scope="col">Opponent</th>
            <th scope="col">Venue</th>
            <th className="num" scope="col">Score</th>
            <th scope="col">Result</th>
            <th className="num" scope="col">Mins</th>
            <th className="num" scope="col">Rating</th>
            <th className="num" scope="col">G</th>
            <th className="num" scope="col">A</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row.fixture_id)}>
              <td>{row.date ? formatDate(row.date) : "—"}</td>
              <td>{row.competition}</td>
              <td>{row.opponent}</td>
              <td>{row.venue ?? "—"}</td>
              <td className="num">
                {row.score_for === null || row.score_against === null
                  ? "—"
                  : `${row.score_for}–${row.score_against}`}
              </td>
              <td>{row.result ?? "—"}</td>
              <td className="num">{row.minutes ?? "—"}</td>
              <td className="num">
                {row.rating === null ? "—" : formatDecimal(row.rating)}
              </td>
              <td className="num">{row.goals ?? "—"}</td>
              <td className="num">{row.assists ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function PlayerPage({
  params,
}: {
  params: Promise<{ playerId: string }>;
}) {
  const { playerId } = await params;
  const page = getPlayerPage(playerId);
  if (!page) notFound();

  const identity = page.identity;
  const side = sideLabel(identity.side);
  const foot = footLabel(identity.preferred_foot.value);
  const positionData = page.panels.position.data;
  const playingData = page.panels.playing_time.data;
  const performanceData = page.panels.performance.data;
  const recordsData = page.panels.records.data;

  return (
    <ContractPage surface="player-profile" state="full">
      <ProfileHeader
        eyebrow={`Aberdeen profile · Season ${identity.season}`}
        name={identity.full_name || identity.name}
        lede={
          <>
            {identity.role ? (
              <span className="position-with-hint">
                <a className="position-link" href="#position">
                  {identity.role}
                </a>
                <a
                  className="position-hint"
                  href="#position"
                  aria-label="How this position was inferred"
                  title="How this position was inferred"
                >
                  i
                </a>
              </span>
            ) : (
              "Position unavailable"
            )}
            {identity.age ? ` · age ${identity.age}` : ""}
            {identity.nationality ? ` · ${identity.nationality}` : ""}
            {identity.number ? ` · squad number ${identity.number}` : ""}
          </>
        }
        attributes={
          side || foot ? (
            <>
              {[side, foot].filter(Boolean).join(" · ")}
              {foot && identity.preferred_foot.source?.url ? (
                <>
                  {" · "}
                  <a
                    href={identity.preferred_foot.source.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    source
                  </a>
                </>
              ) : null}
            </>
          ) : null
        }
        badges={
          <>
            <span className={statusClass(identity.status)}>{statusText(identity)}</span>
            {identity.injured ? <span className="badge badge-warn">Injured</span> : null}
            {identity.loan?.since ? (
              <span className="badge badge-neutral">
                Since {formatDate(identity.loan.since)}
                {identity.loan.end_date ? ` · to ${formatDate(identity.loan.end_date)}` : ""}
              </span>
            ) : null}
          </>
        }
      />

      {page.panels.profile.data ? (
        <PlayerRose
          rose={page.panels.profile.data.rose}
          playerName={identity.full_name || identity.name}
          idPrefix={`player-${page.player_id}`}
          catalogue={page.panels.profile.data.rose_catalogue}
        />
      ) : null}

      <ProfileSection
        id="key-facts"
        eyebrow="Key facts"
        title="Season summary"
        badge={page.panels.profile.data?.summary.league_label}
        indicator="basis"
        contract="player-profile.summary"
      >
        <KeyFacts page={page} />
      </ProfileSection>

      <Panel panel={page.panels.position} id="position">
        {positionData ? (
          <RoleInferenceContent
            model={{
              display_role: positionData.display_role,
              role: positionData.role,
              career_role: positionData.career_role,
              club_history: positionData.club_history,
              tactical_notes: positionData.tactical_notes,
              href: identity.href,
            }}
          />
        ) : null}
      </Panel>

      <Panel panel={page.panels.playing_time} id="playing-time">
        {playingData ? <PlayingTimeView data={playingData} /> : null}
      </Panel>

      <Panel panel={page.panels.performance} id="performance" contract="player-profile.output">
        {performanceData ? <PerformanceView data={performanceData} /> : null}
      </Panel>

      <Panel panel={page.panels.availability} id="availability" contract="player-profile.context">
        {page.panels.availability.data ? (
          <AvailabilityView data={page.panels.availability.data} />
        ) : null}
      </Panel>

      <Panel panel={page.panels.recent_matches} id="recent-matches" contract="player-profile.context">
        {page.panels.recent_matches.data ? (
          <RecentMatchesView rows={page.panels.recent_matches.data} />
        ) : null}
      </Panel>

      {page.panels.records.status === "available" && recordsData ? (
        <Panel panel={page.panels.records} id="records">
          <PerformanceTable columns={RECORD_COLUMNS} rows={recordsData} />
        </Panel>
      ) : null}

      <ProfileSection
        eyebrow="Coverage and limits"
        title="What this profile can and cannot say"
        badge="Source · API-Football"
        contract="player-profile.coverage"
      >
        <p>
          The rose uses Premiership-only rates and compares with the same league and role
          cohort at the cohort minutes threshold. Provider values are opaque and league-relative;
          the cohort percentile is not a cross-league verdict. Availability comes from the
          curated ledger and keeps its source and verification date. No contracts, wages, fees or
          recommendations are claimed.
        </p>
      </ProfileSection>

      <p className="back-link">
        <Link href="/squad/">← Current squad</Link>
        {" · "}
        <Link href="/matchday/">Matchday</Link>
        {" · "}
        <Link href="/scouting/">Scouting comparison</Link>
        {" · "}
        <Link href="/recruitment/">Off the pitch</Link>
      </p>
    </ContractPage>
  );
}
