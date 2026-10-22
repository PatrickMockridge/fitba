import Link from "next/link";

export const metadata = {
  title: "Clubs · fitba",
  robots: { index: false },
};

export default function ClubsPage() {
  return (
    <section className="page-head">
      <p className="eyebrow">Moved</p>
      <h1>Club profiles have moved</h1>
      <p className="lede">
        The old Aberdeen dashboard tried to be a club profile, transfer board,
        shape report and news page at once. The matchday dashboard now answers
        the immediate question before the next game.
      </p>
      <div className="hero-actions">
        <Link className="button" href="/matchday/">
          Matchday dashboard
        </Link>
        <Link className="button button-ghost" href="/squad/">
          Current squad
        </Link>
        <Link className="button button-ghost" href="/scotland/">
          The pyramid
        </Link>
      </div>
    </section>
  );
}
