import Link from "next/link";

export const metadata = { title: "Loans · fitba" };

export default function LoansPage() {
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Aberdeen out on loan</p>
        <h1>Loanee tracker</h1>
        <p className="lede">
          Minutes, goals, assists and position-specific development, labelled by what the
          data actually is. The lower tiers are the hard part — and the most important.
        </p>
        <span className="badge badge-warn">Register ready · first verified entries pending</span>
      </section>

      <div className="empty-state card">
        <h2>No verified loans published yet</h2>
        <p>
          The loan register is curated, not guessed. An entry is published only when it has
          a club announcement or equivalent source, a loan club, dates and a recall flag.
          Machine suggestions are reviewed separately and never auto-published.
        </p>
        <p className="fine-print">
          Add entries in <code>reference/loans.yaml</code>, then run{" "}
          <code>uv run fitba publish</code>.
        </p>
      </div>

      <div className="grid three-col">
        <section className="card">
          <p className="eyebrow">Coverage · event</p>
          <h2>Premiership</h2>
          <p>
            Event and player-match data where verified: minutes, xG/xA, progressive actions,
            defensive actions and adjusted percentiles.
          </p>
        </section>
        <section className="card">
          <p className="eyebrow">Coverage · match</p>
          <h2>Championship</h2>
          <p>
            Appearances and basic output where available. Rich event metrics are shown only
            when the source covers the fixture.
          </p>
        </section>
        <section className="card">
          <p className="eyebrow">Coverage · curated</p>
          <h2>League One &amp; Two</h2>
          <p>
            No free rich player feed exists here. Minutes and output come from a curated
            match log with a source and verification date per row — and the UI says so.
          </p>
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <div>
            <p className="eyebrow">Development view</p>
            <h2>What a loanee card will show</h2>
          </div>
        </div>
        <ul className="plain-list">
          <li>Minutes share of the loan club&apos;s available minutes.</li>
          <li>Goals, assists and xG/xA where the source supports it.</li>
          <li>League-adjusted output compared with Aberdeen options at the same position.</li>
          <li>Alerts for bench-warming, standout output, injury and recall windows.</li>
          <li>A coverage badge and a link to every source used.</li>
        </ul>
        <Link className="text-link" href="/methodology/">
          How coverage and adjustments work →
        </Link>
      </section>
    </>
  );
}
