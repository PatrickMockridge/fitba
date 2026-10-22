import Link from "next/link";
import { NewsGrid } from "@/components/NewsGrid";
import { PlayerLink } from "@/components/PlayerLink";
import { RumourCard } from "@/components/RumourCard";
import { XTimeline } from "@/components/XTimeline";
import { getAberdeen, getForumSignal, getManifest, getRumours } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/news/" }, title: "Aberdeen news & rumours · fitba" };

export default function NewsPage() {
  const aberdeen = getAberdeen();
  const manifest = getManifest();
  const rumours = getRumours();
  const forum = getForumSignal();
  const latestRumours = rumours?.rumours.slice(0, 3) ?? [];
  if (!aberdeen || !aberdeen.news.length) {
    return (
      <section className="empty-state">
        <h1>No news published</h1>
        <p>Run <code>uv run fitba news</code> and then republish.</p>
      </section>
    );
  }
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Aberdeen FC · Season {aberdeen.season}</p>
        <h1>Latest from Pittodrie</h1>
        <p className="lede">
          Two tempos: the high-frequency, unedited club voice on X, and the
          lower-frequency official articles from afc.co.uk. The X timeline is
          embedded from X, not ingested or stored by fitba.
        </p>
        {manifest ? (
          <span className="badge badge-neutral">
            {aberdeen.news.length} official articles ingested
          </span>
        ) : null}
      </section>

      <section className="section" id="x">
        <div className="section-head">
          <div>
            <p className="eyebrow">High frequency · X</p>
            <h2>Live from @aberdeenfc</h2>
          </div>
          <a
            className="text-link"
            href="https://x.com/aberdeenfc"
            target="_blank"
            rel="noreferrer"
          >
            Follow on X →
          </a>
        </div>
        <div className="grid two-col">
          <div className="card x-embed-card">
            <XTimeline handle="AberdeenFC" />
          </div>
          <div className="card">
            <p className="eyebrow">Two feeds, two tempos</p>
            <h3>High frequency is not the same as high confidence</h3>
            <p>
              X is where the club posts quickly: team news, matchday updates,
              reactions and short notices. It is immediate and unedited. The
              official article listing below is slower, but gives fuller context
              and a stable link. If your browser blocks the embed, use the
              fallback link in its place.
            </p>
            <p>
              The X timeline is an embedded third-party widget. Posts may require
              an X login, and fitba does not ingest, store or republish them.
            </p>
            <p className="fine-print">
              If the embed does not load, use the “Open @aberdeenfc on X” link
              below it.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">The bridge · rumours</p>
            <h2>Between the club and the crowd</h2>
          </div>
          <Link className="text-link" href="/rumours/">
            Rumour mill →
          </Link>
        </div>
        <div className="grid two-col">
          <div className="card">
            <p>
              Official news is the club&apos;s voice. The rumour mill is curated,
              sourced and labelled; it is not the transfer register. A rumour
              that becomes business links to the confirmed record.
            </p>
            {latestRumours.length ? (
              <div className="rumour-grid">
                {latestRumours.map((rumour) => (
                  <RumourCard key={rumour.rumour_id} rumour={rumour} />
                ))}
              </div>
            ) : (
              <p className="muted">
                No curated rumours yet. The register is deliberately empty until a
                link has a public source.
              </p>
            )}
          </div>
          <div className="card">
            <p className="eyebrow">Fan signal</p>
            <h3>What the forum is discussing</h3>
            {forum?.signals.length ? (
              <ul className="signal-list">
                {forum.signals.slice(0, 8).map((signal) => (
                  <li key={`${signal.player_name}-${signal.player_key ?? ""}`}>
                    <PlayerLink name={signal.player_name} href={signal.player_href} />
                    <span className="muted">{signal.mentions} mentions</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No fan signal ingested yet.</p>
            )}
            <p className="fine-print">
              Sampled first pages of AFC Chat&apos;s Rumour Mill. Mention counts
              only; no raw posts, usernames or quotes are published.
            </p>
            <Link className="text-link" href="/rumours/">
              Cross-references and sentiment →
            </Link>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Low frequency · official</p>
            <h2>Club articles</h2>
          </div>
        </div>
        <NewsGrid articles={aberdeen.news} />
      </section>

      <p className="fine-print">
        The article grid publishes listing metadata only; article bodies and
        images are not copied. Source:{" "}
        <a href="https://www.afc.co.uk/en/news" target="_blank" rel="noreferrer">
          afc.co.uk/en/news
        </a>
        . Refreshed by the daily pipeline.
      </p>
      <Link className="text-link" href="/matchday/">
        Matchday dashboard →
      </Link>
    </>
  );
}
