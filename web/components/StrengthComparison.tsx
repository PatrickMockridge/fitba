import { TableFrame, Th } from "@/components/TableFrame";
import type { MatchdayDocument, MatchdayStrength } from "@/lib/data";

const METRICS: Array<{
  key: keyof MatchdayStrength;
  label: string;
  percentile: string;
  suffix?: string;
  lowerIsBetter?: boolean;
}> = [
  { key: "ppg", label: "Points per game", percentile: "ppg" },
  { key: "gf_pg", label: "Goals for / game", percentile: "gf_pg" },
  { key: "ga_pg", label: "Goals against / game", percentile: "ga_pg", lowerIsBetter: true },
  { key: "gd_pg", label: "Goal difference / game", percentile: "gd_pg" },
  { key: "shots_for_pm", label: "Shots for / game", percentile: "shots_for_pm" },
  { key: "shot_share", label: "Shot share", percentile: "shot_share", suffix: "%" },
];

function display(value: unknown, suffix = "") {
  if (value === null || value === undefined) return "—";
  if (suffix === "%" && typeof value === "number") {
    return `${Math.round(value * 100)}%`;
  }
  return `${value}${suffix}`;
}

export function StrengthComparison({
  aberdeenName,
  opponentName,
  aberdeen,
  opponent,
  comparison,
}: {
  aberdeenName: string;
  opponentName: string;
  aberdeen: MatchdayStrength;
  opponent: MatchdayStrength;
  comparison: MatchdayDocument["strength_comparison"];
}) {
  if (aberdeen.status !== "available" || opponent.status !== "available") {
    return (
      <section className="section">
        <h2>How do they compare?</h2>
        <p className="muted">
          No current league table is available for one or both teams, so no
          comparison is made.
        </p>
      </section>
    );
  }

  return (
    <section className="section">
      <div className="section-head">
        <h2>How do they compare?</h2>
        <span className="muted">Same league</span>
      </div>

      <p className="page-summary">
        {aberdeenName} {aberdeen.position}th on {aberdeen.points} points ·{" "}
        {opponentName} {opponent.position}th on {opponent.points} points ·{" "}
        {comparison.descriptor ?? "table gap unknown"}
        {comparison.ppg_gap !== null && comparison.ppg_gap !== undefined
          ? ` (${comparison.ppg_gap > 0 ? "+" : ""}${comparison.ppg_gap} PPG)`
          : ""}
        .
      </p>

      <TableFrame
        label="League comparison"
        caption={`League comparison, ${aberdeenName} and ${opponentName}`}
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
            const abd = aberdeen[metric.key] as number | null | undefined;
            const opp = opponent[metric.key] as number | null | undefined;
            const abdPct = aberdeen.percentiles?.[metric.percentile];
            const oppPct = opponent.percentiles?.[metric.percentile];
            return (
              <tr key={metric.key}>
                <td>
                  {metric.label}
                  {metric.lowerIsBetter ? (
                    <span className="muted"> · lower is better</span>
                  ) : null}
                </td>
                <td className="num">
                  {display(abd, metric.suffix)}
                  {abdPct !== null && abdPct !== undefined ? (
                    <span className="muted"> ({abdPct}th)</span>
                  ) : null}
                </td>
                <td className="num">
                  {display(opp, metric.suffix)}
                  {oppPct !== null && oppPct !== undefined ? (
                    <span className="muted"> ({oppPct}th)</span>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </TableFrame>
    </section>
  );
}
