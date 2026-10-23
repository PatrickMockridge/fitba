import Link from "next/link";
import type { ScoutingValueModel } from "@/lib/data";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";

function stateLabel(state: string): string {
  if (state === "ready") return "Fitted from anchors";
  if (state === "fit_failed") return "Anchor fit failed";
  return "Awaiting anchors";
}

function stateBadge(state: string) {
  if (state === "ready") return "badge-ok";
  if (state === "fit_failed") return "badge-warn";
  return "badge-neutral";
}

export function ScoutingValueModelCard({ model }: { model: ScoutingValueModel }) {
  const gate = model.gate;
  const weights = model.index?.weights ?? {};
  const ageCurve = model.index?.age_curve ?? [];
  return (
    <>
      <div className="card-head">
        <div>
          <p className="eyebrow">Value model</p>
          <h2>Scouting value, not a transfer fee</h2>
        </div>
        <span className={`badge ${stateBadge(model.state)}`}>{stateLabel(model.state)}</span>
      </div>
      <p>
        The value index is a 0–100 ordering from the league-adjusted percentile, age, minutes
        and profile fit. It is <strong>not</strong> a transfer value. A GBP band is fitted only
        when the public-source anchor register passes the gate below.
      </p>
      <div className="stat-row four">
        <div className="stat-tile">
          <span className="stat-label">Value index weights</span>
          <span className="stat-value">{formatPercentValue((weights.performance ?? 0) * 100, 0)}</span>
          <span className="stat-note">performance · plus age, minutes, profile</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Usable anchors</span>
          <span className="stat-value">{formatInteger(model.usable_anchors)}</span>
          <span className="stat-note">of {formatInteger(gate.min_anchors)} required</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">League tiers</span>
          <span className="stat-value">{formatInteger(gate.league_tiers)}</span>
          <span className="stat-note">of {formatInteger(gate.min_league_tiers)} required</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Top-tier share</span>
          <span className="stat-value">{formatPercentValue(gate.top_tier_share * 100, 0)}</span>
          <span className="stat-note">of {formatPercentValue(gate.top_tier_required * 100, 0)} required</span>
        </div>
      </div>
      <p className="fine-print">
        Gate: {gate.passed ? "passed" : "not met"}; role coverage{" "}
        {Object.entries(gate.role_counts).map(([role, count]) => `${role} ${count}`).join(", ") ||
          "none"}
        ; age bands {formatInteger(gate.age_bands)}.
      </p>
      {model.state === "ready" && model.sample ? (
        <p className="fine-print">
          Fitted on {formatInteger(model.sample)} anchors: in-sample MAE{" "}
          {formatDecimal(model.in_sample_mae ?? 0, 2)}, LOOCV MAE{" "}
          {formatDecimal(model.loocv_mae ?? 0, 2)}, R² {formatDecimal(model.r2 ?? 0, 2)}.
          The published band is an {formatPercentValue(model.interval * 100, 0)} prediction
          interval, not a fee.
        </p>
      ) : (
        <p className="fine-print" data-contract-indicator="unknown">
          No GBP band is published. The anchor register needs{" "}
          {formatInteger(Math.max(0, gate.min_anchors - model.usable_anchors))} more usable
          public-source anchors before the model can be fitted. Until then the search shows the
          value index and “Awaiting anchors”, never an uncalibrated currency number.
        </p>
      )}
      <details>
        <summary>Index definition and limits</summary>
        <p className="fine-print">
          weights: performance {formatDecimal(weights.performance ?? 0, 2)}, age{" "}
          {formatDecimal(weights.age ?? 0, 2)}, minutes{" "}
          {formatDecimal(weights.minutes ?? 0, 2)}, profile{" "}
          {formatDecimal(weights.profile ?? 0, 2)}. Minimum absolute weight coverage{" "}
          {formatDecimal(model.index?.min_weight_coverage ?? 0, 2)}; full minutes{" "}
          {formatInteger(model.index?.minutes_full ?? 0)}. Age curve:{" "}
          {ageCurve.map((band) => `≤${band.max_age}: ${formatDecimal(band.factor, 2)}`).join(" · ")}.
          Contract length, wages, release clauses and agent fees are unknown and are not
          modelled.
        </p>
        <ul className="plain-list">
          {model.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="fine-print">
          Sources: <Link href="/sources/">sources and licences</Link>; method:{" "}
          <Link href="/methodology/">the method</Link>.
        </p>
      </details>
    </>
  );
}
