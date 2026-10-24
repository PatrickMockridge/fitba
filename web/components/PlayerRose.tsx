import type { RoseAxis, RoseBlock, RoseCatalogue, RoseFigure } from "@/lib/rose";
import { formatDecimal, formatPercentValue } from "@/lib/format";

const SIZE = 320;
const CENTRE = SIZE / 2;
const MAX_RADIUS = 96;
const LABEL_RADIUS = 116;

function point(angle: number, radius: number): { x: number; y: number } {
  return {
    x: CENTRE + radius * Math.cos(angle),
    y: CENTRE + radius * Math.sin(angle),
  };
}

function sectorPath(start: number, end: number, radius: number): string {
  const from = point(start, radius);
  const to = point(end, radius);
  return `M ${CENTRE} ${CENTRE} L ${formatDecimal(from.x)} ${formatDecimal(
    from.y,
  )} A ${formatDecimal(radius)} ${formatDecimal(radius)} 0 0 1 ${formatDecimal(
    to.x,
  )} ${formatDecimal(to.y)} Z`;
}

function definitionFor(axis: RoseAxis, catalogue: RoseCatalogue) {
  return catalogue[axis.metric] ?? { label: axis.metric, short: axis.metric, unit: "per90" as const, direction: "positive" as const };
}

function valueText(axis: RoseAxis, catalogue: RoseCatalogue): string {
  if (axis.value === null) return "—";
  return definitionFor(axis, catalogue).unit === "percent"
    ? formatPercentValue(axis.value, 1)
    : formatDecimal(axis.value, 2);
}

function percentileText(axis: RoseAxis): string {
  return axis.percentile === null ? "—" : formatPercentValue(axis.percentile, 1);
}

function anchorFor(angle: number): "start" | "middle" | "end" {
  const cosine = Math.cos(angle);
  if (cosine > 0.25) return "start";
  if (cosine < -0.25) return "end";
  return "middle";
}

function RoseChart({
  figure,
  idPrefix,
  playerName,
  catalogue,
  seasonNote,
}: {
  figure: RoseFigure;
  idPrefix: string;
  playerName: string;
  catalogue: RoseCatalogue;
  seasonNote?: string | null;
}) {
  const axes = figure.axes;
  const step = (Math.PI * 2) / Math.max(1, axes.length);
  const gap = Math.min(0.045, step * 0.08);
  const titleId = `${idPrefix}-${figure.id}-title`;
  const descId = `${idPrefix}-${figure.id}-desc`;
  const available = figure.status !== "unavailable";
  const top = [...axes]
    .filter((axis) => axis.percentile !== null)
    .sort((left, right) => (right.percentile ?? 0) - (left.percentile ?? 0))
    .slice(0, 3)
    .map((axis) => `${definitionFor(axis, catalogue).label} ${percentileText(axis)}`)
    .join(", ");
  const values = axes
    .map(
      (axis) =>
        `${definitionFor(axis, catalogue).label}: ${percentileText(axis)} percentile, value ${valueText(axis, catalogue)}, cohort n ${axis.cohort_n}`,
    )
    .join("; ");

  return (
    <figure className="rose-figure" data-rose-figure={figure.id}>
      <figcaption>
        <span className="eyebrow">{figure.label}</span>
        <span className={`badge ${figure.status === "available" ? "badge-ok" : "badge-warn"}`}>
          {figure.status === "available" ? "Full" : figure.status === "partial" ? "Partial" : "Unavailable"}
        </span>
      </figcaption>
      <svg
        className="rose-svg"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-labelledby={`${titleId} ${descId}`}
      >
        <title id={titleId}>
          {playerName} {figure.label.toLowerCase()}
        </title>
        <desc id={descId}>
          {`${seasonNote ? `${seasonNote} ` : ""}${
            available
              ? `Nightingale rose of percentile ranks against the player's comparison cohort. ${
                  top ? `Highest axes: ${top}. ` : ""
                } ${values || "No configured axes."}`
              : `No comparable cohort was available for the ${figure.label.toLowerCase()}.`
          }`}
        </desc>
        <g aria-hidden="true">
          {[25, 50, 75, 100].map((ring) => (
            <circle
              key={ring}
              className="rose-ring"
              cx={CENTRE}
              cy={CENTRE}
              r={formatDecimal(MAX_RADIUS * Math.sqrt(ring / 100))}
            />
          ))}
          {axes.map((axis, index) => {
            const angle = -Math.PI / 2 + index * step;
            const end = point(angle, LABEL_RADIUS);
            return (
              <line
                key={`spoke-${axis.metric}`}
                className="rose-spoke"
                x1={CENTRE}
                y1={CENTRE}
                x2={formatDecimal(end.x)}
                y2={formatDecimal(end.y)}
              />
            );
          })}
          {axes.map((axis, index) => {
            if (axis.percentile === null || axis.percentile <= 0) return null;
            const angle = -Math.PI / 2 + index * step;
            const radius = MAX_RADIUS * Math.sqrt(Math.min(100, axis.percentile) / 100);
            return (
              <path
                key={`petal-${axis.metric}`}
                className="rose-petal"
                d={sectorPath(angle - step / 2 + gap, angle + step / 2 - gap, radius)}
              >
                <title>
                  {`${definitionFor(axis, catalogue).label}: ${percentileText(axis)} percentile, value ${valueText(axis, catalogue)}, cohort n ${axis.cohort_n}`}
                </title>
              </path>
            );
          })}
          {axes.map((axis, index) => {
            const angle = -Math.PI / 2 + index * step;
            const label = point(angle, LABEL_RADIUS);
            return (
              <text
                key={`label-${axis.metric}`}
                className="rose-axis-label"
                x={formatDecimal(label.x)}
                y={formatDecimal(label.y)}
                textAnchor={anchorFor(angle)}
                dominantBaseline="middle"
              >
                {definitionFor(axis, catalogue).short}
              </text>
            );
          })}
        </g>
      </svg>
    </figure>
  );
}

export function PlayerRose({
  rose,
  playerName,
  idPrefix,
  catalogue,
}: {
  rose: RoseBlock;
  playerName: string;
  idPrefix: string;
  catalogue: RoseCatalogue;
}) {
  return (
    <div className="rose-block" data-contract="player-profile.rose">
      <div className="card-head">
        <div>
          <p className="eyebrow">Statistical profile</p>
          <h2>Overall and position profile</h2>
        </div>
        <span className="badge badge-neutral">
          {rose.league_label}
          {rose.fallback && rose.season_used ? ` · ${rose.season_used}` : ""}
        </span>
      </div>
      {rose.fallback ? (
        <p className="fine-print" data-contract="player-profile.rose-season">
          {rose.fallback_note ??
            `Showing ${rose.season_used} statistics; the current season is below the profile threshold.`}
        </p>
      ) : rose.status === "unavailable" && rose.fallback_note ? (
        <p className="fine-print" data-contract="player-profile.rose-season">
          {rose.fallback_note}
        </p>
      ) : null}
      <p className="fine-print" data-contract-indicator="basis">
        {`League-only rates. Both figures compare with the same ${
          rose.basis === "provider_group"
            ? "provider position group"
            : rose.basis === "role_family"
              ? "role-family"
              : "no comparable"
        } cohort at ${rose.cohort_min_minutes}+ minutes (n=${rose.cohort_n}). Percentiles run 0-100; areas are proportional to the percentile. A missing value omits its petal rather than drawing zero.`}
      </p>
      {rose.minutes < rose.cohort_min_minutes ? (
        <p className="fine-print">
          {`Player has ${rose.minutes} league minutes, below the ${rose.cohort_min_minutes}-minute cohort; the percentiles are indicative.`}
        </p>
      ) : null}
      <div className="grid two-col rose-grid">
        {rose.figures.map((figure) => (
          <RoseChart
            key={figure.id}
            figure={figure}
            idPrefix={idPrefix}
            playerName={playerName}
            catalogue={catalogue}
            seasonNote={rose.fallback_note}
          />
        ))}
      </div>
    </div>
  );
}
