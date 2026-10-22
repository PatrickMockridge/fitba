import { TableFrame, Th } from "@/components/TableFrame";
import type { StylePair, StyleProfile } from "@/lib/data";

function value(value: number | null | undefined, suffix = "") {
  return value === null || value === undefined ? "—" : `${value}${suffix}`;
}

function share(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

const METRICS: Array<{
  label: string;
  key: keyof StyleProfile;
  format?: (value: number | null | undefined) => string;
}> = [
  { label: "Shots for", key: "shots_for_pm" },
  { label: "Shots against", key: "shots_against_pm" },
  { label: "Shot share", key: "shot_share", format: share },
  { label: "Goals for", key: "goals_for_pm" },
  { label: "Goals against", key: "goals_against_pm" },
];

function leanLine(name: string, pair: StylePair) {
  const index = pair.lean.approach_index;
  return `${name}: ${pair.lean.label}${index !== null && index !== undefined ? ` (${index}/100)` : ""} · ${pair.lean.confidence} confidence`;
}

export function StyleMatchup({
  aberdeenName,
  opponentName,
  aberdeen,
  opponent,
}: {
  aberdeenName: string;
  opponentName: string;
  aberdeen: StylePair;
  opponent: StylePair;
  venueLabel?: string;
}) {
  return (
    <section className="section">
      <div className="section-head">
        <h2>Who imposes what?</h2>
        <span className="muted">League · venue split</span>
      </div>

      <p className="page-summary">
        {leanLine(aberdeenName, aberdeen)}. {leanLine(opponentName, opponent)}.
      </p>

      <TableFrame
        label="Style comparison"
        caption={`Shot profile comparison, ${aberdeenName} and ${opponentName}`}
      >
        <thead>
          <tr>
            <Th>Metric</Th>
            <Th className="num">{aberdeenName}</Th>
            <Th className="num">{opponentName}</Th>
          </tr>
        </thead>
        <tbody>
          {METRICS.map((metric) => {
            const abd = aberdeen.venue[metric.key] as number | null | undefined;
            const opp = opponent.venue[metric.key] as number | null | undefined;
            return (
              <tr key={metric.label}>
                <td>{metric.label}</td>
                <td className="num">
                  {metric.format ? metric.format(abd) : value(abd)}
                </td>
                <td className="num">
                  {metric.format ? metric.format(opp) : value(opp)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </TableFrame>

      <details className="page-legend">
        <summary>Why this read</summary>
        <div className="page-legend-body">
          <p className="muted">
            {aberdeenName}: {aberdeen.venue.matches} venue matches.{" "}
            {aberdeen.lean.evidence.join(" ")}
          </p>
          <p className="muted">
            {opponentName}: {opponent.venue.matches} venue matches.{" "}
            {opponent.lean.evidence.join(" ")}
          </p>
          <p>
            Possession is unknown and is not used. The lean is inferred from
            shots, shot share, shots on target and goals; it is not xG.
          </p>
        </div>
      </details>
    </section>
  );
}
