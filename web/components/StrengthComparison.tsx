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

function Bar({
  percentile,
  side,
}: {
  percentile?: number | null;
  side: "aberdeen" | "opponent";
}) {
  if (percentile === null || percentile === undefined) {
    return <span className="compare-bar is-empty" />;
  }
  return (
    <span className={`compare-bar compare-${side}`}>
      <span style={{ width: `${Math.max(2, Math.min(100, percentile))}%` }} />
    </span>
  );
}

export function StrengthComparison({
  aberdeenName,
  opponentName,
  aberdeen,
  opponent,
  comparison,
  aberdeenFirst,
  contract,
}: {
  aberdeenName: string;
  opponentName: string;
  aberdeen: MatchdayStrength;
  opponent: MatchdayStrength;
  comparison: MatchdayDocument["strength_comparison"];
  aberdeenFirst: boolean;
  contract?: string;
}) {
  if (aberdeen.status !== "available" || opponent.status !== "available") {
    return (
      <section className="card" data-contract={contract}>
        <div className="section-head">
          <div>
            <p className="eyebrow">Relative strength</p>
            <h2>League comparison</h2>
          </div>
          <span className="badge badge-neutral">Unavailable</span>
        </div>
        <p className="muted" data-contract-indicator="unknown">
          No current league table is available for one or both teams, so no
          percentile comparison is made.
        </p>
      </section>
    );
  }

  const leftIsAberdeen = aberdeenFirst;
  const left = leftIsAberdeen ? aberdeen : opponent;
  const right = leftIsAberdeen ? opponent : aberdeen;
  const leftName = leftIsAberdeen ? aberdeenName : opponentName;
  const rightName = leftIsAberdeen ? opponentName : aberdeenName;
  const leftSide: "aberdeen" | "opponent" = leftIsAberdeen
    ? "aberdeen"
    : "opponent";
  const rightSide: "aberdeen" | "opponent" = leftIsAberdeen
    ? "opponent"
    : "aberdeen";

  return (
    <section className="card strength-compare" data-contract={contract}>
      <div className="section-head">
        <div>
          <p className="eyebrow">Relative strength · same league</p>
          <h2>League comparison</h2>
        </div>
        <span className="badge badge-neutral">
          {aberdeen.played ?? 0} matches each
        </span>
      </div>
      <div className="compare-head">
        <span className={leftIsAberdeen ? "is-aberdeen" : undefined}>
          {leftName}
        </span>
        <span className="muted">Metric</span>
        <span className={leftIsAberdeen ? undefined : "is-aberdeen"}>
          {rightName}
        </span>
      </div>
      <div className="compare-rows">
        {METRICS.map((metric) => {
          const leftValue = left[metric.key] as number | null | undefined;
          const rightValue = right[metric.key] as number | null | undefined;
          const leftPct = left.percentiles?.[metric.percentile];
          const rightPct = right.percentiles?.[metric.percentile];
          return (
            <div className="compare-row" key={metric.key}>
              <div
                className={`compare-side${leftIsAberdeen ? " is-aberdeen" : ""}`}
              >
                <span className="compare-value">
                  {display(leftValue, metric.suffix)}
                </span>
                <Bar percentile={leftPct} side={leftSide} />
                <span className="compare-percentile">
                  {leftPct === null || leftPct === undefined
                    ? "—"
                    : `${leftPct}th`}
                </span>
              </div>
              <div className="compare-label">
                {metric.label}
                {metric.lowerIsBetter ? (
                  <span className="fine-print"> lower is better</span>
                ) : null}
              </div>
              <div
                className={`compare-side compare-side-right${
                  leftIsAberdeen ? "" : " is-aberdeen"
                }`}
              >
                <span className="compare-percentile">
                  {rightPct === null || rightPct === undefined
                    ? "—"
                    : `${rightPct}th`}
                </span>
                <Bar percentile={rightPct} side={rightSide} />
                <span className="compare-value">
                  {display(rightValue, metric.suffix)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="stat-row four">
        {[
          { name: leftName, data: left, isAberdeen: leftIsAberdeen },
          { name: rightName, data: right, isAberdeen: !leftIsAberdeen },
        ].map((team) => (
          <div
            key={team.isAberdeen ? "aberdeen" : "opponent"}
            className={`stat-tile${team.isAberdeen ? " is-aberdeen" : ""}`}
          >
            <span className="stat-label">{team.name}</span>
            <span className="stat-value">{team.data.position}th</span>
            <span className="stat-note">
              {team.data.points} pts · {team.data.gf}–{team.data.ga}
            </span>
          </div>
        ))}
        <div className="stat-tile">
          <span className="stat-label">Table gap</span>
          <span className="stat-value">{comparison.descriptor ?? "Unknown"}</span>
          <span className="stat-note">
            {comparison.ppg_gap !== null && comparison.ppg_gap !== undefined
              ? `${comparison.ppg_gap > 0 ? "+" : ""}${comparison.ppg_gap} PPG`
              : "PPG unavailable"}
          </span>
        </div>
        <div className="stat-tile" data-contract-indicator="confidence">
          <span className="stat-label">Read confidence</span>
          <span className="stat-value">{comparison.confidence ?? "unknown"}</span>
          <span className="stat-note">
            {comparison.cross_tier ? "cross-tier · raw values only" : "same league"}
          </span>
        </div>
      </div>
      <p className="fine-print">{comparison.note}</p>
    </section>
  );
}
