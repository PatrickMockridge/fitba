import Link from "next/link";
import { getManifest } from "@/lib/data";

export const metadata = { title: "Method and sources · fitba" };

export default function MethodologyPage() {
  const manifest = getManifest();
  const sources = manifest?.sources ?? [];
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Method</p>
        <h1>How this is built</h1>
        <p className="lede">
          A results-first foundation, then a carefully labelled player layer. The guiding
          rule is simple: never present a derived or curated number as if it were measured
          event data.
        </p>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Sources</p>
            <h2>What feeds the app</h2>
          </div>
          <span className="badge badge-neutral">Schema {manifest?.schema_version ?? "—"}</span>
        </div>
        <div className="table-wrap">
          <table className="league-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Publication lane</th>
                <th className="num">Rows</th>
                <th>Last checked</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>{source.name}</td>
                  <td>
                    <code>{source.lane}</code>
                  </td>
                  <td className="num">{source.rows.toLocaleString("en-GB")}</td>
                  <td>{source.last_verified ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print">
          Football-Data.co.uk is the results source. Raw payloads are never committed;
          the app publishes computed tables and aggregates with attribution.
        </p>
      </section>

      <div className="grid two-col">
        <section className="card">
          <p className="eyebrow">Tables</p>
          <h2>Computed, not scraped</h2>
          <p>
            Points are 3W + D, goal difference and goals scored break ties, then a
            head-to-head mini-league. Playoff matches are excluded. Points deductions are
            stored in <code>reference/disciplinary.yaml</code> with a citation and applied
            before ranking; the raw and adjusted points are both retained.
          </p>
        </section>
        <section className="card">
          <p className="eyebrow">Uncertainty</p>
          <h2>Assumptions are labelled</h2>
          <p>
            League-strength adjustment uses Elo where available and a documented prior
            otherwise, with a confidence flag and sensitivity check. Budget fit is fee-only
            until a ceiling is set; individual Scottish wages are not public and are never
            invented.
          </p>
        </section>
        <section className="card">
          <p className="eyebrow">Coverage</p>
          <h2>Event, match, curated, value-only</h2>
          <p>
            Every league and player carries a coverage tier. League One/Two player data is
            curated because no free rich feed exists; the card says so. A value-only player
            is never ranked against event-data peers without a warning.
          </p>
        </section>
        <section className="card">
          <p className="eyebrow">2D viewer</p>
          <h2>Reconstructed, not tracked</h2>
          <p>
            Goals and key passages are rebuilt from event coordinates. Only the ball and
            the players involved in each event are placed from source coordinates; other
            tokens are inferred from formation and average position. Every sequence will
            carry an “event-reconstructed — not tracking data” badge.
          </p>
        </section>
      </div>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Policy</p>
            <h2>What is not published</h2>
          </div>
        </div>
        <ul className="plain-list">
          <li>No raw source payloads, full event feeds or source-shaped tables.</li>
          <li>No raw market-value feeds; only bands and our derived scores.</li>
          <li>No club crests or player photographs without a licence.</li>
          <li>No odds in the public app.</li>
          <li>No affiliation with Aberdeen FC, the SPFL or any provider.</li>
        </ul>
        <p className="fine-print">
          A source can be disabled in <code>config/sources.yaml</code> and the site rebuilt
          from the remaining sources. See <code>docs/sources.md</code> and{" "}
          <code>DATA_LICENSE.md</code>.
        </p>
        <Link className="text-link" href="/status/">
          Data status and freshness →
        </Link>
      </section>
    </>
  );
}
