import type { FixtureDocument } from "@/lib/data";

const LABELS: Record<string, string> = {
  events: "Events",
  lineups: "Lineups",
  team_stats: "Team stats",
  player_stats: "Player stats",
  xg: "fxG",
  depth: "Depth",
};

export function MatchCoverage({ coverage }: { coverage: FixtureDocument["coverage"] }) {
  return (
    <section className="card match-coverage" data-contract="match.coverage">
      <div className="section-head">
        <div>
          <p className="eyebrow">Coverage</p>
          <h2>What this page can show</h2>
        </div>
        <span className="badge badge-neutral">{String(coverage.depth ?? "unknown")}</span>
      </div>
      <ul className="coverage-list">
        {Object.entries(coverage)
          .filter(([key]) => key !== "note")
          .map(([key, value]) => (
            <li key={key}>
              <span>{LABELS[key] ?? key}</span>
              <strong>{typeof value === "boolean" ? (value ? "available" : "unavailable") : String(value)}</strong>
            </li>
          ))}
      </ul>
      <p className="fine-print">{String(coverage.note ?? "")}</p>
    </section>
  );
}
