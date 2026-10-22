import type { CaseCoverage as Coverage } from "@/lib/data";

export function CaseCoverage({ coverage }: { coverage: Coverage }) {
  return (
    <section className="card case-coverage" data-contract="case.coverage">
      <div className="section-head">
        <div>
          <p className="eyebrow">Coverage</p>
          <h2>What the record cannot say</h2>
        </div>
        <span className="badge badge-neutral">{coverage.status}</span>
      </div>
      <div className="case-two-col">
        <div>
          <h3>Availability</h3>
          <p>{coverage.availability_feed}</p>
          <h3>History</h3>
          <p>{coverage.historical_appearances}</p>
        </div>
        <div>
          <h3>Not measured</h3>
          <ul className="plain-list">
            {coverage.missing.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
      <p className="fine-print">{coverage.note}</p>
    </section>
  );
}
