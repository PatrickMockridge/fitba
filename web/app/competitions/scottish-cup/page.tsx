import Link from "next/link";
import { CupRound } from "@/components/CupRound";
import { formatDate, getScottishCup } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/competitions/scottish-cup/" }, title: "Scottish Cup · fitba" };

export default function ScottishCupPage() {
  const cup = getScottishCup();
  if (!cup) {
    return (
      <section className="empty-state">
        <h1>No Scottish Cup data</h1>
        <p>Run <code>uv run fitba cups</code> and <code>uv run fitba publish</code>.</p>
      </section>
    );
  }

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Cup · Season {cup.season}</p>
        <h1>{cup.name}</h1>
        <p className="lede">
          A pure knockout: 137 clubs, 136 ties, single-leg with extra time and
          penalties. The 12 Premiership clubs enter in the fourth round on 16
          January 2027. Aberdeen are among them.
        </p>
        <div className="hero-actions">
          <Link className="button button-ghost" href="/competitions/">
            All competitions
          </Link>
          <Link className="button button-ghost" href="/sources/">
            Source coverage
          </Link>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>
              {cup.coverage.licensed_ties} of {cup.coverage.official_ties} ties
            </h2>
          </div>
          <span className="badge badge-warn">Partial licensed feed</span>
        </div>
        <p>{cup.coverage.note}</p>
        <p className="fine-print">
          Present: {cup.coverage.rounds_present.join(", ") || "none"}. Not
          provided: {cup.coverage.rounds_missing.join(", ") || "none"}.
        </p>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <p className="eyebrow">Aberdeen</p>
            <h2>
              {cup.aberdeen.entry_round ?? "Fourth Round"}
              {cup.aberdeen.entry_date
                ? ` · ${formatDate(cup.aberdeen.entry_date)}`
                : ""}
            </h2>
          </div>
          <span className="badge badge-warn">{cup.aberdeen.status}</span>
        </div>
        <p>{cup.aberdeen.note}</p>
        <p className="fine-print">
          No tie is shown until the draw is published. The page does not invent
          an opponent.
        </p>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Rounds</p>
            <h2>Round by round</h2>
          </div>
        </div>
        <div className="pyramid-stack">
          {cup.rounds.map((round) => (
            <div className="card" key={round.name}>
              <CupRound round={round} highlightTeamId="sco:aberdeen" />
            </div>
          ))}
        </div>
      </section>

      <p className="fine-print">
        Source: {cup.source.name}, checked {cup.source.verified_at ?? "—"}. The
        licensed feed is partial; rounds it does not provide are labelled rather
        than filled with invented ties.
      </p>
      <Link className="text-link" href="/competitions/">
        ← All competitions
      </Link>
    </>
  );
}
