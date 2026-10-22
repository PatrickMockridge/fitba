import Link from "next/link";
import { BucketBars } from "@/components/BucketBars";
import { ForumSignalPanel } from "@/components/ForumSignalPanel";
import { PlayerLink } from "@/components/PlayerLink";
import { RumourBoard } from "@/components/RumourBoard";
import {
  getForumSignal,
  getRumourProfile,
  getRumours,
  getTransfers,
} from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/rumours/" }, title: "Rumour mill · fitba" };

export default function RumoursPage() {
  const rumours = getRumours();
  const profile = getRumourProfile();
  const forum = getForumSignal();
  const transfers = getTransfers();

  if (!rumours) {
    return (
      <section className="empty-state">
        <h1>Rumour mill not published</h1>
        <p>
          Run <code>uv run fitba publish</code> to generate the rumour register and
          fan-signal payloads.
        </p>
      </section>
    );
  }

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Off the pitch · Season {rumours.season}</p>
        <h1>The rumour mill</h1>
        <p className="lede">
          Aberdeen-linked rumours, curated with sources and an editorial
          confidence, plus a rule-based read of what fans are saying. This is not
          the confirmed register: completed business lives in{" "}
          <Link href="/transfers/">transfers</Link>.
        </p>
        <div className="hero-actions">
          <span className="badge badge-warn">Not the confirmed register</span>
          <span className="badge badge-neutral">{rumours.summary.total} curated links</span>
          <span className="badge badge-neutral">{forum?.signals.length ?? 0} fan signals</span>
        </div>
      </section>

      <section className="card">
        <p className="eyebrow">Legend</p>
        <h2>How to read a rumour card</h2>
        <ul className="plain-list">
          <li>
            <strong>Status:</strong> <code>active</code>, <code>denied</code>,{" "}
            <code>confirmed</code> or <code>stale</code>. It is a lifecycle label,
            not a probability.
          </li>
          <li>
            <strong>Confidence:</strong> <code>low</code>, <code>medium</code> or{" "}
            <code>high</code>. It is editorial and must be explained by the linked
            sources.
          </li>
          <li>
            <strong>Source types:</strong> <code>press</code>,{" "}
            <code>journalist</code>, <code>forum</code> or <code>club</code>.
          </li>
          <li>
            <strong>Engagement:</strong> none. Votes, polls and submissions are a
            deferred separate project, so no counts are shown.
          </li>
        </ul>
      </section>

      <section className="card separation-banner">
        <h2>Rumours and confirmed business are different registers</h2>
        <p>
          A rumour here is an unconfirmed link. It becomes <strong>confirmed</strong>{" "}
          only when the move is in the transfer register, and then it links to that
          row. Status is a lifecycle label, not a probability. Confidence is
          editorial and must be explained by the linked sources. No fabricated
          quotes, no player abuse, no betting framing.
        </p>
        <p className="fine-print">
          {rumours.coverage.note} {rumours.notes}
        </p>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Curated register</p>
            <h2>Aberdeen-linked rumours</h2>
          </div>
          <Link className="text-link" href="/transfers/">
            Confirmed business →
          </Link>
        </div>
        <RumourBoard data={rumours} />
      </section>

      {rumours.opinions.length ? (
        <section className="section">
          <div className="section-head">
            <div>
              <p className="eyebrow">Opinion</p>
              <h2>Data-backed positions</h2>
            </div>
          </div>
          <div className="grid two-col">
            {rumours.opinions.map((opinion) => (
              <article className="card opinion-card" key={opinion.opinion_id}>
                <span className="badge badge-warn">{opinion.label}</span>
                <h3>{opinion.title}</h3>
                <p>{opinion.body}</p>
                <p className="fine-print">
                  Stance: {opinion.stance} · Evidence: {opinion.evidence.join(", ")}
                </p>
                {opinion.player_mentions?.length ? (
                  <p className="fine-print">
                    Mentions:{" "}
                    {opinion.player_mentions.map((mention, index) => (
                      <span key={mention.href}>
                        {index ? ", " : ""}
                        <PlayerLink name={mention.name} href={mention.href} />
                      </span>
                    ))}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Recruitment profile</p>
            <h2>What the active links imply</h2>
          </div>
          <Link className="text-link" href="/scouting/">
            Scouting overlay →
          </Link>
        </div>
        <div className="card">
          <p>{profile?.narrative}</p>
          {profile && profile.sample_size > 0 && profile.low_confidence ? (
            <span className="badge badge-warn">
              Small cohort ({profile.sample_size}) — advisory, not a target list
            </span>
          ) : null}
          <p className="fine-print">{profile?.note}</p>
        </div>
        <div className="grid two-col">
          <div className="card">
            <BucketBars title="Position mix" buckets={profile?.buckets.position ?? {}} />
            <BucketBars title="Age mix" buckets={profile?.buckets.age_band ?? {}} />
          </div>
          <div className="card">
            <BucketBars title="League mix" buckets={profile?.buckets.league ?? {}} />
            <BucketBars title="Value mix" buckets={profile?.buckets.value_band ?? {}} />
          </div>
        </div>
        {profile?.signals.length ? (
          <div className="table-wrap">
            <table className="league-table compact">
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Position</th>
                  <th className="num">Age</th>
                  <th>League</th>
                  <th>Value</th>
                  <th>Confidence</th>
                  <th className="num">Weight</th>
                </tr>
              </thead>
              <tbody>
                {profile.signals.map((signal) => (
                  <tr key={signal.rumour_id}>
                    <td>
                      <PlayerLink name={signal.player_name} href={signal.player_href} />
                    </td>
                    <td>{signal.position ?? "—"}</td>
                    <td className="num">{signal.age ?? "—"}</td>
                    <td>{signal.league ?? "—"}</td>
                    <td>{signal.value_band ?? "—"}</td>
                    <td>{signal.confidence}</td>
                    <td className="num">{signal.weight}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="section">
        <ForumSignalPanel data={forum} limit={16} />
      </section>

      <section className="section">
        <div className="card engagement-card">
          <p className="eyebrow">Separate project</p>
          <h2>Community engagement is not built here</h2>
          <p>
            Votes, polls, rumour submissions and comments need identity,
            moderation, rate limiting, a data store and a privacy policy. The
            static app has no backend, so this page shows no vote counts and no
            local-only widget pretending to be a shared community.
          </p>
          <p className="fine-print">
            Deferred by design. See <code>config/engagement.yaml</code> and{" "}
            <Link href="/methodology/">the method page</Link> for the researched
            options and the requirements before anything ships.
          </p>
        </div>
      </section>

      <p className="back-link">
        <Link href="/recruitment/">← Off the pitch</Link>
        {transfers ? (
          <>
            {" · "}
            <Link href="/transfers/">Confirmed transfer register →</Link>
          </>
        ) : null}
      </p>
    </>
  );
}
