import type { FixtureDocument } from "@/lib/data";

function Basis({ value }: { value: string }) {
  return (
    <span className="basis-badge" data-contract-indicator="basis">
      {value}
    </span>
  );
}

export function MatchSummary({ summary }: { summary: FixtureDocument["summary"] }) {
  return (
    <section className="card match-summary" data-contract="match.summary">
      <div className="section-head">
        <div>
          <p className="eyebrow">The read</p>
          <h2>{summary.headline}</h2>
        </div>
        <Basis value={summary.basis} />
      </div>
      <ul className="read-list">
        {summary.bullets.map((bullet, index) => (
          <li key={index}>
            <span>{bullet.text}</span>
            <Basis value={bullet.basis} />
          </li>
        ))}
      </ul>
      {summary.reconciliation?.matched === false ? (
        <p className="fine-print">
          The event feed and the final score do not reconcile. The score is
          authoritative; the timeline is incomplete.
        </p>
      ) : null}
      {summary.reconciliation?.matched === null ? (
        <p className="fine-print">
          Event reconciliation is unavailable; the final score is authoritative.
        </p>
      ) : null}
      <p className="fine-print">{summary.note}</p>
    </section>
  );
}
