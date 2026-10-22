import { StatTile } from "@/components/StatTile";

interface RecordBlock {
  gf?: number;
  ga?: number;
  points?: number;
  gf_pg?: number | null;
  ga_pg?: number | null;
  shots_for_pm?: number | null;
  shots_against_pm?: number | null;
  shot_share?: number | null;
  conversion?: number | null;
}

interface BalanceMetrics {
  season?: RecordBlock;
  last_five?: RecordBlock;
  goals_by_family?: {
    attack?: number;
    midfield?: number;
    defence?: number;
    total?: number;
    attack_share?: number | null;
  };
  coverage?: Record<string, unknown>;
}

function pct(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

export function BalancePanel({ metrics }: { metrics: BalanceMetrics }) {
  const season = metrics.season ?? {};
  const recent = metrics.last_five ?? {};
  const mix = metrics.goals_by_family ?? {};
  const total = mix.total ?? 0;
  const rows = [
    { label: "Attack (W/ST)", value: mix.attack ?? 0 },
    { label: "Midfield", value: mix.midfield ?? 0 },
    { label: "Defence / GK", value: mix.defence ?? 0 },
  ];
  return (
    <div className="balance-panel">
      <div className="section-head">
        <div>
          <p className="eyebrow">League only</p>
          <h3>Goals and shots balance</h3>
        </div>
        <span className="badge badge-neutral">No xG</span>
      </div>
      <div className="stat-row four">
        <StatTile
          label="Season goals"
          value={`${season.gf ?? "—"}–${season.ga ?? "—"}`}
          note={`${season.points ?? "—"} points`}
        />
        <StatTile
          label="Goals / game"
          value={season.gf_pg ?? "—"}
          note={`conceded ${season.ga_pg ?? "—"}`}
        />
        <StatTile
          label="Shot share"
          value={pct(season.shot_share)}
          note={`${season.shots_for_pm ?? "—"} for · ${season.shots_against_pm ?? "—"} against`}
        />
        <StatTile
          label="Last five"
          value={`${recent.gf ?? "—"}–${recent.ga ?? "—"}`}
          note={`${recent.points ?? "—"} points`}
        />
      </div>
      <div className="goal-mix">
        <p className="eyebrow">League goals by primary role</p>
        {rows.map((row) => (
          <div className="goal-mix-row" key={row.label}>
            <span>{row.label}</span>
            <span className="goal-mix-track">
              <span
                style={{
                  width: `${total ? Math.max(2, (row.value / total) * 100) : 0}%`,
                }}
              />
            </span>
            <span className="goal-mix-value">
              {row.value} ({total ? `${Math.round((row.value / total) * 100)}%` : "—"})
            </span>
          </div>
        ))}
      </div>
      <p className="fine-print">
        The forward share is real, but this is a descriptive balance, not proof
        that the forwards are carrying the defence. No xG or shot-quality model
        is available.
      </p>
    </div>
  );
}
