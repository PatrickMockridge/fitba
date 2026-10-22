import Link from "next/link";

export const metadata = {
  title: "Page not found · fitba",
  robots: { index: false, follow: true },
};

export default function NotFound() {
  return (
    <section className="empty-state">
      <p className="eyebrow">404</p>
      <h1>That page is off target</h1>
      <p>The club, tier or match is not in this build.</p>
      <Link className="button" href="/">
        Back to home
      </Link>
    </section>
  );
}
