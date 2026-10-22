import Link from "next/link";

export const metadata = { title: "About · fitba" };

export default function AboutPage() {
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">About</p>
        <h1>The data, for the stand and the analyst</h1>
        <p className="lede">
          fitba is the translation layer between the data that shapes Scottish
          football and the people who watch it. The same evidence, in the same
          language, with the context and uncertainty that hot takes leave out.
        </p>
      </section>

      <div className="grid two-col">
        <section className="card">
          <p className="eyebrow">The problem</p>
          <h2>Two tiers, rarely meeting</h2>
          <p>
            Football has an analysis tier that works in percentiles, budgets, age
            curves and uncertainty, and a spectator tier that watches results,
            form and individual mistakes. Attempts to bridge them are often
            one-dimensional: a single rating, a &ldquo;data says&rdquo; take, or a
            chart with no explanation.
          </p>
          <p>
            That leaves fans frustrated and certain in the wrong places, blaming
            individuals for structural trade-offs they were never shown.
          </p>
        </section>

        <section className="card">
          <p className="eyebrow">The promise</p>
          <h2>Same evidence, not insider knowledge</h2>
          <p>
            We do not have Aberdeen&apos;s internal models, wage structure or board
            discussions. We show the publicly observable proxies a back room works
            from — minutes, roles, output, style, squad age and value, budget
            bands, contracts and loans — and explain the questions they raise.
          </p>
          <p>
            Every panel separates what is <strong>measured</strong>,{" "}
            <strong>inferred</strong>, <strong>curated</strong> and{" "}
            <strong>unknown</strong>.
          </p>
        </section>
      </div>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Principles</p>
            <h2>How the site is built</h2>
          </div>
        </div>
        <ul className="plain-list">
          <li>
            <strong>Evidence before narrative, context before blame.</strong> A
            drought is shown with role, minutes, shot quality, team style and
            sample size — not a verdict.
          </li>
          <li>
            <strong>Progressive disclosure.</strong> Headline, visual, what it
            means, then the method. Casual fans stop at the first; analysts can go
            all the way down.
          </li>
          <li>
            <strong>Uncertainty is a feature.</strong> Sample-size badges, coverage
            tiers and confidence are visible. We never fake precision.
          </li>
          <li>
            <strong>Show the trade-offs, not villains.</strong> A trading club
            creates value and volatility. Both are part of the story.
          </li>
          <li>
            <strong>One framework, many clubs.</strong> Aberdeen, opponents and
            scouted players are measured the same way.
          </li>
          <li>
            <strong>Independent and correctable.</strong> Non-commercial, no
            betting advertising, a corrections route, and no claim to speak for
            the club.
          </li>
        </ul>
      </section>

      <div className="grid two-col">
        <section className="card">
          <p className="eyebrow">Aberdeen</p>
          <h2>The trading club</h2>
          <p>
            Aberdeen have operated as a trading club: buy low, develop, sell high,
            reinvest in young players. The model has had commercial success, grown
            the fanbase and delivered a Scottish Cup. It has also produced volatile
            league form since Dave Cormack&apos;s chairmanship.
          </p>
          <p>
            That is a trade-off, not a villain. The app shows the logic — value,
            youth minutes, sell-on income, wage discipline — and the costs: squad
            turnover, replacement risk and week-to-week variance.
          </p>
          <p className="fine-print">
            Club-context statements reflect the project owner&apos;s framing, not an
            audited financial or boardroom account.
          </p>
        </section>

        <section className="card">
          <p className="eyebrow">Sources and limits</p>
          <h2>No licence landmines</h2>
          <p>
            Public data comes from a licensed feed or an official club/federation
            listing whose terms permit the use. We do not scrape sources that
            prohibit it. Unlicensed event or tracking data stays local and is never
            published.
          </p>
          <p>
            Basic stats, budgets and transfers can be shown now. Event coordinates
            and tracking require a separate licensed contract; the 2D viewer will
            be event-reconstructed, not tracking, and will say so.
          </p>
          <div className="pill-row">
            <span className="pill">measured</span>
            <span className="pill">inferred</span>
            <span className="pill">curated</span>
            <span className="pill">unknown</span>
          </div>
          <Link className="text-link" href="/sources/">
            Source and licence detail →
          </Link>
        </section>
      </div>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">What we will not build</p>
            <h2>The line</h2>
          </div>
        </div>
        <ul className="plain-list">
          <li>Player ratings presented as verdicts, or &ldquo;data says sign him&rdquo; certainty.</li>
          <li>Blame narratives without role, sample and context.</li>
          <li>Raw scraped data, unlicensed Opta/Sofascore feeds or betting odds.</li>
          <li>Invented wages, fees or internal valuations.</li>
          <li>Unmoderated forum posts or unsourced links presented as fact.</li>
          <li>Fake community vote counts before the engagement project exists.</li>
          <li>A full tracking visual before the licensed data and audience justify it.</li>
        </ul>
        <Link className="text-link" href="/methodology/">
          Read the methodology →
        </Link>
      </section>
    </>
  );
}
