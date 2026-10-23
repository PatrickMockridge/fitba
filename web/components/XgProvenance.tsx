import type { XgDocument, XgProviderEstimate } from "@/lib/data";
import { formatDecimal } from "@/lib/format";

function dec(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : formatDecimal(value);
}

function dec4(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : formatDecimal(value, 4);
}

export function XgProvenance({
  estimate,
  evaluation,
  coverage,
}: {
  estimate: XgProviderEstimate | null;
  evaluation: XgDocument["evaluation"];
  coverage: XgDocument["coverage"];
}) {
  return (
    <section className="card" data-contract="xg.provenance">
      <div className="section-head">
        <div>
          <p className="eyebrow">Where the numbers come from</p>
          <h2>Two different xG measures, never blended</h2>
        </div>
        <span className="badge badge-neutral">Method</span>
      </div>
      <div className="grid three-col">
        <section className="mini-block">
          <h3>fitba fxG</h3>
          <p>
            Shots on target multiplied by an empirical-Bayes competition-season
            conversion rate, with an 80% interval and match-to-match
            overdispersion.
          </p>
          <p className="fine-print">
            League shots come from football-data.co.uk; cup and European shots
            from API-Football. The model has no shot locations, opponent
            adjustment or home advantage. The provider-xG gate is{" "}
            <strong>
              {evaluation?.status === "fail"
                ? "failed"
                : evaluation?.status ?? "unavailable"}
            </strong>
            , so fxG remains descriptive.
          </p>
        </section>
        <section className="mini-block">
          <h3>Provider xG actual</h3>
          <p>
            football-data.co.uk 2026-27 SC0 supplies HxG/AxG for the league;
            API-Football supplies expected goals for some cup and European
            matches.
          </p>
          <p className="fine-print">
            Aberdeen actual coverage: {coverage.provider_actual?.league_2026_27 ?? 0}{" "}
            league matches in 2026-27,{" "}
            {coverage.provider_actual?.league_2025_26 ?? 0} in 2025-26, and{" "}
            {coverage.provider_actual?.conference_2025_26 ?? 0} European matches in
            2025-26. The European rows were under a different manager and are not
            part of the league manager split.
          </p>
        </section>
        <section className="mini-block">
          <h3>Provider-style estimate</h3>
          {estimate?.status === "available" ? (
            <>
              <p>
                Fitted on {estimate.sample.matches} league matches /{" "}
                {estimate.sample.team_rows} team rows:{" "}
                <code>
                  provider estimate = max(0,{" "}
                  {dec4(estimate.coefficients?.intercept)} +{" "}
                  {dec4(estimate.coefficients?.slope)} × fxG)
                </code>
                .
              </p>
              <p className="fine-print">
                In-sample MAE {dec(estimate.in_sample_mae)}; leave-one-row-out MAE{" "}
                {dec(estimate.loocv_mae)}; maximum LOOCV error{" "}
                {dec(estimate.max_loocv_error)}; R² {dec(estimate.r2)}.
              </p>
            </>
          ) : (
            <p className="fine-print">
              No estimate is published: {estimate?.reason ?? "insufficient sample"}.
            </p>
          )}
          <p className="fine-print">
            This is an estimate, not provider xG. Provider xG uses shot locations
            and a provider model; this record has no shot coordinates. Using the
            calibration does not mean the gate has passed.
          </p>
        </section>
      </div>
    </section>
  );
}
