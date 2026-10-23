import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { XgTable } from "@/components/XgTable";
import { getXg } from "@/lib/data";
import { formatDecimal } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/analysis/xg/" },
  title: "fxG model · fitba",
  description:
    "fitba's shot-on-target expected goals model, its interval, its provider-xG evaluation and its limitations.",
};

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
  return (
    <ContractPage surface="analysis-xg">
      <section className="page-head" data-contract="xg.hero">
        <p className="eyebrow">Model · {data.model.model_id}</p>
        <h1>fxG</h1>
        <p className="lede">
          fitba&apos;s own expected goals from shots on target, with an 80%
          model interval. It is not provider xG and it is not a result
          prediction.
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
            <h2>{gatePassed ? "Provider-xG gate passed" : "Descriptive model only"}</h2>
          </div>
          <span className={`badge ${gatePassed ? "badge-positive" : "badge-negative"}`}>
            {evaluation?.status ?? "unavailable"}
          </span>
        </div>
        <div className="case-two-col">
          <div>
            <h3>What it does</h3>
            <p>
              Estimates a competition-season on-target conversion rate with an
              empirical-Bayes prior, multiplies it by shots on target, and widens
              the interval for match-to-match overdispersion.
            </p>
            <h3>What it does not do</h3>
            <p>
              It does not see shot location, goalkeeper positioning or game
              state. It does not adjust for opponent or home advantage. It does
              not replace provider xG where provider xG exists.
            </p>
          </div>
          <div>
            <h3>Fit</h3>
            <p>
              {data.model.fit_matches} team-match rows; seasons{" "}
              {data.model.fit_seasons.join(", ")}. Overdispersion{" "}
              {formatDecimal(data.model.overdispersion)}.
            </p>
            <h3>Evaluation</h3>
            {evaluation ? (
              <ul className="plain-list">
                <li>Validation season: {evaluation.validation_season}</li>
                <li>Matches with provider xG: {evaluation.matches}</li>
                <li>Team-match rows with provider xG: {evaluation.team_rows ?? "—"}</li>
                <li>Bias: {evaluation.bias ?? "—"}</li>
                <li>MAE: {evaluation.mae ?? "—"}</li>
                <li>Calibration slope: {evaluation.calibration_slope ?? "—"}</li>
              </ul>
            ) : (
              <p>No provider-xG validation is available.</p>
            )}
          </div>
        </div>
        <p className="fine-print">
          {evaluation?.note ??
            "Provider xG is an external benchmark, not the model target."}
        </p>
      </section>

      <XgTable aggregates={data.aggregates} />

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
        </ul>
        <p className="fine-print">{data.coverage.note}</p>
      </section>
    </ContractPage>
  );
}
