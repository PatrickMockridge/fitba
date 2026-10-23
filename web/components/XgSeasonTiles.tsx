import { StatTile } from "@/components/StatTile";
import type { XgManagerSplit, XgProviderEstimate } from "@/lib/data";
import { formatDecimal, formatSigned } from "@/lib/format";

function dec(value: number | null) {
  return value === null ? "—" : formatDecimal(value);
}

function signed(value: number | null) {
  return value === null ? "—" : formatSigned(value);
}

function perMatch(value: number | null, matches: number) {
  if (value === null || matches === 0) return "—";
  return `${formatDecimal(value / matches)} per match`;
}

function providerLabel(
  row: XgManagerSplit,
  estimate: XgProviderEstimate | null,
) {
  if (row.provider_basis === "actual") return "actual · for / against";
  if (row.provider_basis === "actual_partial") {
    return `actual ${row.provider_actual_matches}/${row.matches} · for / against`;
  }
  if (row.provider_basis === "estimate" && estimate?.status === "available") {
    return "estimate · for / against";
  }
  return "unavailable";
}

function providerValues(row: XgManagerSplit) {
  if (row.provider_basis === "actual" || row.provider_basis === "actual_partial") {
    if (row.provider_actual_for === null && row.provider_actual_against === null) return "—";
    return `${dec(row.provider_actual_for)} / ${dec(row.provider_actual_against)}`;
  }
  if (row.provider_basis === "estimate") {
    if (row.provider_estimate_for === null && row.provider_estimate_against === null) return "—";
    return `${dec(row.provider_estimate_for)} / ${dec(row.provider_estimate_against)}`;
  }
  return "—";
}

function SeasonGroup({
  title,
  row,
  estimate,
}: {
  title: string;
  row: XgManagerSplit | undefined;
  estimate: XgProviderEstimate | null;
}) {
  if (!row) return null;
  return (
    <div className="mini-block">
      <p className="eyebrow">{title}</p>
      <div className="stat-row four">
        <StatTile
          label="fxG for"
          value={dec(row.fxg_for)}
          note={perMatch(row.fxg_for, row.matches)}
        />
        <StatTile
          label="fxG against"
          value={dec(row.fxg_against)}
          note={perMatch(row.fxg_against, row.matches)}
        />
        <StatTile
          label="Goals"
          value={`${row.goals_for} / ${row.goals_against}`}
          note={`for / against · goals − fxG ${signed(row.goals_minus_fxg_for)} / ${signed(row.goals_minus_fxg_against)}`}
        />
        <StatTile
          label="Provider xG"
          value={providerValues(row)}
          note={providerLabel(row, estimate)}
        />
      </div>
    </div>
  );
}

export function XgSeasonTiles({
  rows,
  estimate,
}: {
  rows: XgManagerSplit[];
  estimate: XgProviderEstimate | null;
}) {
  const current = rows.find((row) => row.comparison_role === "current");
  const previous = rows.find(
    (row) => row.comparison_role === "previous" && row.season !== current?.season,
  );
  const context = rows.find((row) => row.scope === "season_context");
  const previousSeason = previous?.season ?? context?.season ?? "last season";
  if (!current && !previous) return null;
  return (
    <section className="card" data-contract="xg.season-tiles">
      <div className="section-head">
        <div>
          <p className="eyebrow">fxG and provider xG</p>
          <h2>The same league sample, one season apart</h2>
        </div>
        <span className="badge badge-neutral">League only</span>
      </div>
      <SeasonGroup
        title={`Stephen Robinson · ${current?.season ?? "current"} · ${current?.matches ?? 0} league matches`}
        row={current}
        estimate={estimate}
      />
      <SeasonGroup
        title={`Stephen Robinson · ${previousSeason} · ${previous?.matches ?? 0} league matches`}
        row={previous}
        estimate={estimate}
      />
      {context ? (
        <p className="fine-print">
          Full {context.season}: {context.matches} league matches, fxG{" "}
          {dec(context.fxg_for)} / {dec(context.fxg_against)}, goals{" "}
          {context.goals_for} / {context.goals_against}, provider-xG estimate{" "}
          {dec(context.provider_estimate_for)} /{" "}
          {dec(context.provider_estimate_against)}.
        </p>
      ) : null}
      <p className="fine-print">
        Provider xG is actual for the current season and a calibrated estimate for
        last season; the difference is not a provider trend. The provider-xG gate
        still fails, so all values are descriptive.
      </p>
    </section>
  );
}
