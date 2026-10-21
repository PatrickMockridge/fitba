import Link from "next/link";

export const metadata = { title: "Clubs · fitba" };

export default function ClubsPage() {
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Club profiles</p>
        <h1>Clubs</h1>
        <p className="lede">Aberdeen is the focal club; the rest of the pyramid follows.</p>
      </section>
      <Link className="card tier-card" href="/clubs/aberdeen/">
        <div className="card-head">
          <div>
            <p className="eyebrow">Premiership · Pittodrie</p>
            <h2>Aberdeen</h2>
          </div>
          <span className="club-roundel">AFC</span>
        </div>
        <p>
          League position, results, season history, intended style, squad needs and the
          recruitment budget envelope.
        </p>
        <span className="text-link">Open dashboard →</span>
      </Link>
    </>
  );
}
