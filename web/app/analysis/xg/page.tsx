import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { XgTable } from "@/components/XgTable";
import { getXg } from "@/lib/data";
import { formatDecimal, formatInteger, formatSigned } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/analysis/xg/" },
  title: "fxG model · fitba",
  description:
    "fitba's team-match expected goals, its model and goals ranges, penalties, provider-xG calibration and limitations.",
};

const FEATURE_LABELS: Record<string, string> = {
  open_play_insidebox: "inside-box shots",
  open_play_outsidebox: "outside-box shots",
  open_play_sot: "shots on target",
  open_play_off: "off-target shots",
  open_play_blocked: "blocked shots",
  shots_on_target: "shots on target",
  off_target_shots: "off-target shots",
  intercept: "intercept",
};

function formula(coefficients: Record<string, number> | null | undefined): string {
  if (!coefficients) return "unavailable";
  return Object.entries(coefficients)
    .map(([key, value]) => `${formatDecimal(value, 3)} × ${FEATURE_LABELS[key] ?? key}`)
    .join(" + ");
}

function goalPosition(value: string | null | undefined): string {
  if (value === "above") return "above the 80% goals range";
  if (value === "below") return "below the 80% goals range";
  if (value === "within") return "within the 80% goals range";
  return "position unavailable";
}

export default function XgPage() {
  const data = getXg();
  if (!data || !data.model) {
    return (
      <ContractPage surface="analysis-xg" state="empty">
        <section className="page-head" data-contract="xg.hero">
          <p className="eyebrow">Season overview</p>
          <h1>fxG</h1>
          <p className="lede">
            No fxG document is published in this build. Run{" "}
            <code>uv run fitba publish</code> to generate it.
          </p>
        </section>
      </ContractPage>
    );
  }
  const evaluation = data.evaluation;
  const gatePassed = Boolean(evaluation?.passed);
  const model = data.model;
  const era = data.aggregates.find((row) => row.scope === "era");
  const last10 = data.aggregates.find((row) => row.scope === "last10");
  const selection = model.selection as
    | {
        selected?: string;
        selected_label?: string;
        candidates?: Record<
          string,
          { mae?: number | null; bias?: number | null; calibration_slope?: number | null; passed?: boolean }
        >;
      }
    | null;
  const transfer = model.transfer_check as
    | {
        status?: string;
        season?: string;
        source?: string;
        matches?: number;
        team_rows?: number;
        bias?: number | null;
        mae?: number | null;
        calibration_slope?: number | null;
        model_interval_coverage?: number | null;
        note?: string;
      }
    | null;
  return (
    <ContractPage surface="analysis-xg">
      <section className="page-head" data-contract="xg.hero">
        <p className="eyebrow">Model · {model.model_id}</p>
        <h1>fxG</h1>
        <p className="lede">
          fitba&apos;s team-match expected goals: open-play shot zones, shots on
          target and penalties, fitted to provider xG. It carries an 80% model
          range for the estimate and a separate 80% goals range for the same
          chances. It is not provider xG, not a shot-level location model and
          not a result prediction.
        </p>
        <p className="fine-print">
          <Link className="text-link" href="/analysis/">
            Season overview →
          </Link>{" "}
          <Link className="text-link" href="/methodology/">
            Method →
          </Link>{" "}
          <Link className="text-link" href="/matches/">
            Results and fixtures →
          </Link>
        </p>
      </section>

      <section className="card" data-contract="xg.model">
        <div className="section-head">
          <div>
            <p className="eyebrow">Model card</p>
            <h2>{gatePassed ? "Calibration gate passed" : "Descriptive model only"}</h2>
          </div>
          <span className={`badge ${gatePassed ? "badge-positive" : "badge-negative"}`}>
            {evaluation?.status ?? "unavailable"}
          </span>
        </div>
        <div className="case-two-col">
          <div>
            <h3>What it does</h3>
            <p>
              Estimates open-play expected goals from the selected specification{" "}
              <strong>{selection?.selected_label ?? model.specification ?? "volume"}</strong>:
            </p>
            <code>
              fxG = max(0, {formula(model.coefficients)})
              {model.penalty_xg ? ` + ${formatDecimal(model.penalty_xg, 2)} × penalties` : ""}
            </code>
            <p>
              The coefficients are fitted to 2026-27 Premiership provider xG.
              Penalties are counted separately at {formatDecimal(model.penalty_xg ?? 0, 2)}{" "}
              xG each and removed from the open-play counts. The 80% model range
              is the uncertainty in this estimate.
            </p>
            <h3>What it does not do</h3>
            <p>
              It does not see shot distance, angle, body part, defensive pressure,
              goalkeeper position or post-shot placement. It does not adjust for
              opponent or game state. It is a team-match estimate, not a
              shot-level xG model, not xGOT and not provider xG. It does not
              predict results or rank players.
            </p>
          </div>
          <div>
            <h3>Fit</h3>
            <p>
              {model.fit_matches} matches / {model.fit_team_rows ?? "—"} team rows;{" "}
              {model.fit_season ?? "—"} {model.fit_competition ?? ""}. Features:{" "}
              {(model.features ?? []).join(", ") || "—"}. Bootstrap:{" "}
              {model.bootstrap?.valid_draws ?? 0}/{model.bootstrap?.draws ?? 0} draws,
              clustered by match.
            </p>
            <h3>Evaluation</h3>
            {evaluation ? (
              <ul className="plain-list">
                <li>Validation season: {evaluation.validation_season}</li>
                <li>Method: {evaluation.method ?? "—"}</li>
                <li>Matches with provider xG: {evaluation.matches}</li>
                <li>Team-match rows: {evaluation.team_rows ?? "—"}</li>
                <li>Bias: {evaluation.bias ?? "—"}</li>
                <li>MAE: {evaluation.mae ?? "—"}</li>
                <li>Calibration slope: {evaluation.calibration_slope ?? "—"}</li>
                <li>R²: {evaluation.r2 ?? "—"}</li>
                <li>
                  Model-range coverage:{" "}
                  {evaluation.model_interval_coverage ?? "—"}
                </li>
                <li>
                  Goals-range coverage: {evaluation.goals_range_coverage ?? "—"} (a
                  discrete range can cover more than its nominal level)
                </li>
              </ul>
            ) : (
              <p>No provider-xG validation is available.</p>
            )}
          </div>
        </div>
        {selection?.candidates ? (
          <div className="table-wrap">
            <table className="league-table compact">
              <caption className="fine-print">
                Candidate specifications; the selected model is the gate-eligible
                candidate with the lowest MAE, with a simplicity and penalty tie-break.
              </caption>
              <thead>
                <tr>
                  <th>Spec</th>
                  <th className="num">MAE</th>
                  <th className="num">Bias</th>
                  <th className="num">Slope</th>
                  <th>Gate</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(selection.candidates).map(([key, candidate]) => (
                  <tr key={key}>
                    <td>{key}</td>
                    <td className="num">{candidate.mae ?? "—"}</td>
                    <td className="num">{candidate.bias ?? "—"}</td>
                    <td className="num">{candidate.calibration_slope ?? "—"}</td>
                    <td>{candidate.passed ? "pass" : "fail"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {transfer ? (
          <p className="fine-print" data-contract="xg.provider">
            <strong>Transfer check:</strong> {transfer.matches ?? "—"} matches /{" "}
            {transfer.team_rows ?? "—"} team rows in {transfer.season ?? "—"} from{" "}
            {transfer.source ?? "the provider"}; MAE {transfer.mae ?? "—"}, bias{" "}
            {transfer.bias ?? "—"}, slope {transfer.calibration_slope ?? "—"}.{" "}
            {transfer.note}
          </p>
        ) : null}
        <p className="fine-print">
          {evaluation?.note ??
            "Provider xG is an external benchmark, not the model target."}
        </p>
      </section>

      <section className="card" data-contract="xg.uncertainty">
        <div className="section-head">
          <div>
            <p className="eyebrow">Uncertainty</p>
            <h2>Two ranges, two questions</h2>
          </div>
        </div>
        <div className="case-two-col">
          <div>
            <h3>80% model range</h3>
            <p>
              How uncertain is the fxG estimate? The range is the 10th–90th
              percentile of match-clustered bootstrap predictions plus the
              leave-one-match-out residual pool. It is the uncertainty in the
              number, not a prediction of the score.
            </p>
          </div>
          <div>
            <h3>80% goals range</h3>
            <p>
              How many goals would the same chances produce? Open-play goals use
              a binomial (beta-binomial when dispersion is above one) and
              penalties use a separate binomial at{" "}
              {formatDecimal(model.penalty_xg ?? 0, 2)}. Aggregate distributions
              are convolved, so the width grows with the square root of the
              number of matches. Per-match intervals are never summed.
            </p>
          </div>
        </div>
        <p className="fine-print">
          Goals dispersion: {model.goals_dispersion ?? 1}. Bootstrap:{" "}
          {model.bootstrap?.valid_draws ?? 0} valid draws from{" "}
          {model.bootstrap?.draws ?? 0}, seed {model.bootstrap?.seed ?? "—"}. The
          ranges are descriptive and are not confidence intervals for team
          quality.
        </p>
      </section>

      <XgTable aggregates={data.aggregates} />

      <section className="card" data-contract="xg.overperformance">
        <div className="section-head">
          <div>
            <p className="eyebrow">Finishing</p>
            <h2>Goals minus fxG, and how unusual it is</h2>
          </div>
        </div>
        {era ? (
          <p>
            Era: {formatInteger(era.goals)} goals from {formatDecimal(era.fxg ?? 0, 2)}{" "}
            fxG, a difference of {formatSigned(era.goals_minus_fxg ?? 0)},{" "}
            {goalPosition(era.goals_position)}. The result is descriptive: one
            season is a small sample, finishing overperformance usually regresses,
            and style changes the chance profile without changing the model.
          </p>
        ) : null}
        {last10 ? (
          <p className="fine-print">
            Last 10 league matches: {formatInteger(last10.goals)} goals from{" "}
            {formatDecimal(last10.fxg ?? 0, 2)} fxG,{" "}
            {formatSigned(last10.goals_minus_fxg ?? 0)},{" "}
            {goalPosition(last10.goals_position)}. This is not a verdict on
            finishing skill.
          </p>
        ) : null}
      </section>

      <section className="card" data-contract="xg.style">
        <div className="section-head">
          <div>
            <p className="eyebrow">Style</p>
            <h2>Volume and chance quality are different profiles</h2>
          </div>
        </div>
        {era ? (
          <ul className="plain-list">
            <li>
              Shots: {formatInteger(era.shots)} in {formatInteger(era.matches)} matches;
              shots on target: {formatInteger(era.shots_on_target)}.
            </li>
            <li>
              xG per shot: {era.xg_per_shot === null ? "—" : formatDecimal(era.xg_per_shot, 3)}.
              A volume side can take many lower-quality shots; a selective side can
              take fewer better ones. Neither is better in isolation.
            </li>
            <li>
              Penalties: {formatInteger(era.penalties)} attempts, counted separately.
            </li>
          </ul>
        ) : null}
        <p className="fine-print">
          A low block can concede volume while limiting quality; a high press can
          force low-quality shots or create high-quality turnovers. fxG does not
          adjust for style, opponent or game state. Read xG per shot with shot
          volume, not instead of it.
        </p>
      </section>

      <section className="card" data-contract="xg.coverage">
        <div className="section-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>What the record can support</h2>
          </div>
        </div>
        <ul className="plain-list">
          <li>Played fixtures: {data.coverage.matches}</li>
          <li>Fixtures with fxG: {data.coverage.with_fxg}</li>
          <li>Fixtures with provider xG: {data.coverage.with_provider_xg}</li>
          <li>Fixtures missing team stats: {data.coverage.missing_team_stats}</li>
          {data.coverage.enrichment ? (
            <li>
              Calibration enrichment: {data.coverage.enrichment.api_fixtures_matched}{" "}
              fixtures / {data.coverage.enrichment.stats_available} stat rows;{" "}
              {data.coverage.enrichment.zones_available} with zones;{" "}
              {data.coverage.enrichment.penalties_available} with penalty status.
            </li>
          ) : null}
        </ul>
        <p className="fine-print">{data.coverage.note}</p>
      </section>

      <section className="card" data-contract="xg.provider">
        <div className="section-head">
          <div>
            <p className="eyebrow">Provider xG</p>
            <h2>A separate model, never blended</h2>
          </div>
        </div>
        <p>
          Provider xG is carried where the feed supplies it: football-data.co.uk
          2026-27 SC0 and API-Football where returned. It is a different model,
          uses shot locations and its own training data, and its decimals are not
          comparable across providers. It is never averaged with fxG.
        </p>
        <p className="fine-print">
          There is no xGOT or post-shot xG in this record: goalmouth trajectory is
          not available. Missing provider values are unavailable, not zero.
        </p>
      </section>
    </ContractPage>
  );
}
