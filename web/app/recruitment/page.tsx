import Link from "next/link";
import { BucketBars } from "@/components/BucketBars";
import { ForumSignalPanel } from "@/components/ForumSignalPanel";
import { NeedsBoard } from "@/components/NeedsBoard";
import { RumourCard } from "@/components/RumourCard";
import { StatTile } from "@/components/StatTile";
import { TransferCard } from "@/components/TransferCard";
import {
  getForumSignal,
  getNeeds,
  getRumourProfile,
  getRumours,
  getTransfers,
} from "@/lib/data";

export const metadata = { title: "Off the pitch · fitba" };

export default function RecruitmentPage() {
  const transfers = getTransfers();
  const rumours = getRumours();
  const profile = getRumourProfile();
  const forum = getForumSignal();
  const needs = getNeeds();

  const latestTransfers = transfers?.transfers.slice(0, 4) ?? [];
  const latestRumours = rumours?.rumours.slice(0, 3) ?? [];

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Off the pitch · Season {rumours?.season ?? transfers?.season ?? "—"}</p>
        <h1>Transfers, scouting and the rumour mill</h1>
        <p className="lede">
          The trading side of the club: the squad needs behind the next window,
          confirmed business, the loan register, the scouting method and the
          curated rumour mill. Confirmed transfers and rumours stay in separate
          registers; the needs board is where the themes meet recruitment.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/transfers/">
            Confirmed transfers
          </Link>
          <Link className="button button-ghost" href="/rumours/">
            Rumour mill
          </Link>
          <Link className="button button-ghost" href="/scouting/">
            Scouting
          </Link>
          <Link className="button button-ghost" href="/squad/">
            Current squad
          </Link>
        </div>
      </section>

      {needs ? <NeedsBoard data={needs} /> : null}

      <section className="grid two-col">
        <div className="card">
          <div className="card-head">
            <div>
              <p className="eyebrow">Confirmed business</p>
              <h2>What actually happened</h2>
            </div>
          </div>
          <div className="stat-row">
            <StatTile label="Deals" value={transfers?.summary.total ?? 0} note="three seasons" />
            <StatTile
              label="Confirmed"
              value={transfers?.summary.confirmed ?? 0}
              note="official announcement"
            />
            <StatTile label="Loans out" value={transfers?.loans_out.length ?? 0} note="register" />
            <StatTile label="Loans in" value={transfers?.loans_in.length ?? 0} note="register" />
          </div>
          {latestTransfers.length ? (
            <div className="transfer-grid">
              {latestTransfers.map((transfer) => (
                <TransferCard key={transfer.transfer_id} transfer={transfer} />
              ))}
            </div>
          ) : (
            <p className="muted">No published transfers yet.</p>
          )}
          <Link className="text-link" href="/transfers/">
            Full transfer register →
          </Link>
        </div>

        <div className="card">
          <div className="card-head">
            <div>
              <p className="eyebrow">Rumour mill</p>
              <h2>Curated links, labelled</h2>
            </div>
          </div>
          <p>
            Rumours are curated with a public source, a status and an editorial
            confidence. Status is a lifecycle label, not a probability. A
            confirmed rumour links back to the transfer register; it never
            becomes a second source of truth.
          </p>
          <div className="stat-row">
            <StatTile label="Links" value={rumours?.summary.total ?? 0} note="curated" />
            <StatTile
              label="Active"
              value={rumours?.summary.by_status.active ?? 0}
              note="still live"
            />
            <StatTile
              label="Confirmed"
              value={rumours?.summary.by_status.confirmed ?? 0}
              note="linked to transfers"
            />
            <StatTile
              label="Fan signals"
              value={forum?.signals.length ?? 0}
              note="names mentioned"
            />
          </div>
          {latestRumours.length ? (
            <div className="rumour-grid">
              {latestRumours.map((rumour) => (
                <RumourCard key={rumour.rumour_id} rumour={rumour} />
              ))}
            </div>
          ) : (
            <div className="empty-state compact">
              <h3>No curated rumours yet</h3>
              <p>
                The register is deliberately empty until a link has a public source.
                Fan chatter is shown as a signal, not as a rumour.
              </p>
            </div>
          )}
          <Link className="text-link" href="/rumours/">
            Rumour mill, profile and fan signal →
          </Link>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Recruitment profile</p>
            <h2>What the links say</h2>
          </div>
          <Link className="text-link" href="/scouting/">
            Scouting board →
          </Link>
        </div>
        <div className="grid two-col">
          <div className="card">
            <p>{profile?.narrative ?? "The profile activates when the rumour register has sourced rows."}</p>
            <p className="fine-print">
              {profile
                ? `${profile.sample_size} active link${profile.sample_size === 1 ? "" : "s"} · weighted by editorial confidence and recency (${profile.weights.recency_half_life_days}-day half-life).`
                : "Advisory only; the data-driven fit stays primary."}
            </p>
            {profile && profile.sample_size > 0 && profile.low_confidence ? (
              <span className="badge badge-warn">Small sample — treat as a hint, not a target list</span>
            ) : null}
          </div>
          <div className="card">
            <BucketBars title="Position mix" buckets={profile?.buckets.position ?? {}} />
          </div>
        </div>
      </section>

      <section className="section">
        <ForumSignalPanel data={forum} limit={6} showSentiment={false} showTopics={false} />
        <p className="back-link">
          <Link href="/rumours/">All fan signal and the sentiment comparison →</Link>
          {" · "}
          <Link href="/news/">News &amp; rumours, the bridge →</Link>
          {" · "}
          <Link href="/themes/">The bigger picture →</Link>
        </p>
      </section>
    </>
  );
}
