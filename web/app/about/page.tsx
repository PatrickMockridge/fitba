import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { GullMark } from "@/components/GullMark";
import { getHistory } from "@/lib/data";

export const metadata = { title: "About · fitba" };

export default function AboutPage() {
  const history = getHistory();
  const scorecard = history?.scorecard;
  const honourLabel =
    scorecard && scorecard.honours_total === 1 ? "major honour" : "major honours";

  return (
    <ContractPage surface="about">
      <section className="page-head" data-contract="about.hero">
        <p className="eyebrow">About</p>
        <h1>Aberdeen FC, without the noise.</h1>
        <p className="lede">
          An independent, data-driven record of Aberdeen FC — the numbers, the
          sources and the argument, without the hot takes.
        </p>
      </section>

      <div className="grid two-col">
        <section className="card">
          <p className="eyebrow">The gap</p>
          <h2>One record, two audiences</h2>
          <p>
            Football has an analysis tier that works in percentiles, budgets, age
            curves and uncertainty, and a matchgoing reader who watches results,
            form and individual mistakes. Attempts to connect them are often
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

      <div className="grid two-col">
        <section className="card" data-contract="about.audience">
          <p className="eyebrow">Who this is for</p>
          <h2>Engaged supporters, not a hypothetical median reader</h2>
          <p>
            The primary reader knows the squad, the league and the arguments. They
            may not be a statistician, but they are numerate and want the numbers,
            the sources and the uncertainty. We do not design down to an imagined
            casual fan, and we do not remove evidence to make a page feel lighter.
          </p>
          <p>
            The same record is public so that supporters, the club, the press and
            critics can look at the same evidence. We are independent of the club;
            we are not neutral about its success.
          </p>
        </section>

        <section className="card" data-contract="about.club-side">
          <p className="eyebrow">The line we hold</p>
          <h2>On the club&apos;s side, not in its pocket</h2>
          <p>
            We want Aberdeen to succeed. That is not the same as defending the
            club. Being on the club&apos;s side means taking its problems seriously
            enough to measure them: not softening bad numbers, not turning every
            setback into a morality play, and not treating a bad result as proof
            that a player or a manager is the whole problem.
          </p>
          <p>
            Criticism is aimed at decisions and structures, with evidence. The
            club is not a villain, and neither are its supporters.
          </p>
        </section>
      </div>

      <section className="card city-card" data-contract="about.city">
        <div className="section-head">
          <div>
            <p className="eyebrow">The city and the club</p>
            <h2>Granite, the North Sea, and a one-club city</h2>
          </div>
          <GullMark />
        </div>
        <div className="aurora-rule" />
        <p>
          Aberdeen is the granite city: a one-club city on the North Sea, founded
          in 1903. Pittodrie sits about 500 yards from the water; the gulls
          arrive for the leftovers. The fans sing &ldquo;The Northern Lights of
          Old Aberdeen&rdquo; about the aurora. The traditional derby is the New
          Firm against Dundee United. Glasgow, Edinburgh and Dundee are two-club
          cities; Aberdeen&apos;s identity is not split.
        </p>
        <p className="fine-print">
          This is context, not decoration. The record above it is the point.
        </p>
      </section>

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
            <strong>Layered evidence, not withheld evidence.</strong> Headline,
            visual, what it means, then the method. Substantive panels and sources
            stay visible; deeper method can sit behind disclosure.
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
            betting advertising, a published corrections policy, and no claim to
            speak for the club. We are on the club&apos;s side without being its
            mouthpiece.
          </li>
        </ul>
      </section>

      <div className="grid two-col">
        <section className="card" data-contract="about.cormack">
          <p className="eyebrow">Aberdeen</p>
          <h2>The Cormack era: player, manager, structure</h2>
          {scorecard ? (
            <p>
              Since 16 December 2019 the public record covers{" "}
              {scorecard.seasons} seasons and {scorecard.manager_count} people in
              charge of at least one league match, including interim spells, with
              league finishes from {scorecard.best_position ?? "—"} to{" "}
              {scorecard.worst_position ?? "—"} and {scorecard.honours_total}{" "}
              {honourLabel}. It also contains heavy defeats, including 6-0
              losses, and a winless away run in 2026, alongside two Conference
              League campaigns (the 2023-24 group stage and the 2025-26 league
              phase) and significant player sales.
            </p>
          ) : (
            <p>
              Since 16 December 2019 the public record covers the Cormack era:
              one Scottish Cup, two Conference League campaigns, league finishes
              from third to tenth, heavy defeats and high squad turnover.
            </p>
          )}
          <p>
            That is not a verdict on any one person. It is a set of facts that has
            to be separated into three levels: the player, the manager and the
            structure. fitba&apos;s job is to make each level measurable and to say
            which one the evidence supports. If a pattern is unexplained by the
            model, we say so; we do not fill the gap with a story. Attribution to
            the model, the manager or the players is a labelled reading, not a
            measured conclusion.
          </p>
          <Link className="text-link" href="/history/">
            The full Cormack-era record →
          </Link>
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

      <section className="card" data-contract="about.line">
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
          <li>
            A question in place of a declarative heading, or a contracted table,
            caveat or source hidden because it was judged too much for an imagined
            average reader.
          </li>
        </ul>
        <Link className="text-link" href="/methodology/">
          Read the methodology →
        </Link>
      </section>
    </ContractPage>
  );
}
