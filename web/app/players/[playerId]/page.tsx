import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Panel } from "@/components/Panel";
import { RoleInferenceContent } from "@/components/RoleInference";
import { StatTile } from "@/components/StatTile";
import { formatDate } from "@/lib/format";
import { getPlayerPage, getSquad } from "@/lib/data";
import type { SquadStat } from "@/lib/data";
import type {
  IdentityBlock,
  PerformancePanel,
  PlayerPageDocument,
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
  return {
    title: page ? `${page.identity.full_name || page.identity.name} · fitba` : "Player profile · fitba",
  };
}

function initials(name: string): string {
  const parts = name.replace(/\./g, "").split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?"
  );
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
    <>
      <section className="club-head player-identity">
        <div className="club-identity">
          <span className="club-roundel large">{initials(identity.full_name || identity.name)}</span>
          <div>
            <p className="eyebrow">Player profile · Season {identity.season}</p>
            <h1>{identity.full_name || identity.name}</h1>
            <p className="lede">
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
            </p>
            {side || foot ? (
              <p className="player-attributes">
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
              </p>
            ) : null}
            <div className="hero-actions">
              <span className={statusClass(identity.status)}>{statusText(identity)}</span>
              {identity.injured ? <span className="badge badge-warn">Injured</span> : null}
              {identity.loan?.since ? (
                <span className="badge badge-neutral">
                  Since {formatDate(identity.loan.since)}
                  {identity.loan.end_date ? ` · to ${formatDate(identity.loan.end_date)}` : ""}
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </section>

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

      <Panel panel={page.panels.performance} id="performance">
        {performanceData ? <PerformanceView data={performanceData} /> : null}
      </Panel>

      {page.panels.records.status === "available" && recordsData ? (
        <Panel panel={page.panels.records} id="records">
          <PerformanceTable columns={RECORD_COLUMNS} rows={recordsData} />
        </Panel>
      ) : null}

      <p className="back-link">
        <Link href="/squad/">← Current squad</Link>
        {" · "}
        <Link href="/matchday/">Matchday</Link>
        {" · "}
        <Link href="/recruitment/">Off the pitch</Link>
      </p>
    </>
  );
}
