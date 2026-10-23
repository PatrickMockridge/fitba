import type { XgDocument, XgProviderEstimate } from "@/lib/data";

export function ProviderCoverageNote({
  coverage,
  estimate,
}: {
  coverage: XgDocument["coverage"];
  estimate: XgProviderEstimate | null;
}) {
  const actual = coverage.provider_actual;
  return (
    <section className="card" data-contract="xg.provider-coverage">
      <div className="section-head">
        <div>
          <p className="eyebrow">Coverage</p>
          <h2>What provider xG can and cannot show</h2>
        </div>
        <span className="badge badge-warn">No shot locations</span>
      </div>
      <ul className="plain-list">
        <li>
          <strong>2026-27 league:</strong> {actual?.league_2026_27 ?? 0} actual
          provider-xG matches.
        </li>
        <li>
          <strong>2025-26 league:</strong> {actual?.league_2025_26 ?? 0} actual
          provider-xG matches. The {estimate?.sample.team_rows ?? 0} calibration
          team rows are the estimate&apos;s only evidence; every 2025-26 league
          value is an estimate.
        </li>
        <li>
          <strong>2025-26 Europe:</strong> {actual?.conference_2025_26 ?? 0} actual
          provider matches, all under Thelin, excluded from the league manager
          split.
        </li>
        <li>
          <strong>2023-24 Europe:</strong> {actual?.conference_2023_24 ?? 0} actual
          provider matches, outside this comparison.
        </li>
        <li>
          <strong>Missing team stats:</strong> {coverage.missing_team_stats} played
          fixtures have no shots-on-target row, so fxG is unavailable there, not
          zero.
        </li>
      </ul>
      <p className="fine-print">
        The estimate cannot recover shot-location effects or match-specific
        provider adjustments. It is a calibration on the provider values we have,
        not a reconstruction of the provider&apos;s algorithm.
      </p>
    </section>
  );
}
