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
}: {
  aberdeenName: string;
  opponentName: string;
  aberdeen: MatchdayStrength;
  opponent: MatchdayStrength;
  comparison: MatchdayDocument["strength_comparison"];
}) {
  if (aberdeen.status !== "available" || opponent.status !== "available") {
    return (
      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Relative strength</p>
            <h2>League comparison</h2>
          </div>
          <span className="badge badge-neutral">Unavailable</span>
        </div>
        <p className="muted">
          No current league table is available for one or both teams, so no
          percentile comparison is made.
        </p>
      </section>
    );
  }

  return (
    <section className="card strength-compare">
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
        <span>{aberdeenName}</span>
        <span className="muted">Metric</span>
        <span>{opponentName}</span>
      </div>
      <div className="compare-rows">
        {METRICS.map((metric) => {
          const abd = aberdeen[metric.key] as number | null | undefined;
          const opp = opponent[metric.key] as number | null | undefined;
          const abdPct = aberdeen.percentiles?.[metric.percentile];
          const oppPct = opponent.percentiles?.[metric.percentile];
          return (
            <div className="compare-row" key={metric.key}>
              <div className="compare-side">
                <span className="compare-value">
                  {display(abd, metric.suffix)}
                </span>
                <Bar percentile={abdPct} side="aberdeen" />
                <span className="compare-percentile">
                  {abdPct === null || abdPct === undefined ? "—" : `${abdPct}th`}
                </span>
              </div>
              <div className="compare-label">
                {metric.label}
                {metric.lowerIsBetter ? (
                  <span className="fine-print"> lower is better</span>
                ) : null}
              </div>
              <div className="compare-side compare-side-right">
                <span className="compare-percentile">
                  {oppPct === null || oppPct === undefined ? "—" : `${oppPct}th`}
                </span>
                <Bar percentile={oppPct} side="opponent" />
                <span className="compare-value">
                  {display(opp, metric.suffix)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="stat-row four">
        <div className="stat-tile">
          <span className="stat-label">{aberdeenName}</span>
          <span className="stat-value">{aberdeen.position}th</span>
          <span className="stat-note">
            {aberdeen.points} pts · {aberdeen.gf}–{aberdeen.ga}
          </span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">{opponentName}</span>
          <span className="stat-value">{opponent.position}th</span>
          <span className="stat-note">
            {opponent.points} pts · {opponent.gf}–{opponent.ga}
          </span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Table gap</span>
          <span className="stat-value">{comparison.descriptor ?? "Unknown"}</span>
          <span className="stat-note">
            {comparison.ppg_gap !== null && comparison.ppg_gap !== undefined
              ? `${comparison.ppg_gap > 0 ? "+" : ""}${comparison.ppg_gap} PPG`
              : "PPG unavailable"}
          </span>
        </div>
        <div className="stat-tile">
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
