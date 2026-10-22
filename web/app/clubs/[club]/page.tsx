import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ club: "aberdeen" }];
}

export const metadata = {
  title: "Aberdeen dashboard moved · fitba",
  alternates: { canonical: "/matchday/" },
  robots: { index: false, follow: true },
};

export default async function ClubPage({
  params,
}: {
  params: Promise<{ club: string }>;
}) {
  const { club } = await params;
  if (club !== "aberdeen") notFound();

  return (
    <section className="page-head">
      <p className="eyebrow">Moved</p>
      <h1>The Aberdeen dashboard has moved</h1>
      <p className="lede">
        The matchday dashboard is now the front door: the next fixture, both
        predicted XIs, form, home and away splits, opponent style and the keys
        to the match. The old page tried to be too many things at once.
      </p>
      <div className="hero-actions">
        <Link className="button" href="/matchday/">
          Go to the matchday dashboard
        </Link>
        <Link className="button button-ghost" href="/fixtures/">
          Results &amp; fixtures
        </Link>
        <Link className="button button-ghost" href="/squad/">
          Current squad
        </Link>
        <Link className="button button-ghost" href="/history/">
          The Cormack era
        </Link>
        <Link className="button button-ghost" href="/transfers/">
          Transfers
        </Link>
      </div>
      <p className="fine-print">
        This address is kept as a moved notice for bookmarks. The underlying
        club, squad, history and transfer data are still published.
      </p>
    </section>
  );
}
