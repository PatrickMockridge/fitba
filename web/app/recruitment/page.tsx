import Link from "next/link";
import { BucketBars } from "@/components/BucketBars";
import { ContractPage } from "@/components/ContractPage";
import { DefinitionTerm } from "@/components/DefinitionTerm";
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

export const metadata = {
  alternates: { canonical: "/recruitment/" }, title: "Off the pitch · fitba" };

export default function RecruitmentPage() {
  const transfers = getTransfers();
  const rumours = getRumours();
  const profile = getRumourProfile();
  const forum = getForumSignal();
  const needs = getNeeds();

  const latestTransfers = transfers?.transfers.slice(0, 4) ?? [];
  const latestRumours = rumours?.rumours.slice(0, 3) ?? [];

  return (
    <ContractPage surface="recruitment">
      <section className="page-head" data-contract="recruitment.hero">
        <p className="eyebrow">Off the pitch · Season {rumours?.season ?? transfers?.season ?? "—"}</p>
        <h1>Recruitment, transfers and the squad plan</h1>
        <p className="lede">
          The trading side of the club: the squad needs behind the next window,
          confirmed business, the loan register, the scouting method and the
          <DefinitionTerm id="basis">curated</DefinitionTerm> rumour register.
          Confirmed transfers and rumours stay in separate registers; the needs
          board is where the themes meet recruitment.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/transfers/">
            Confirmed transfers
          </Link>
          <Link className="button button-ghost" href="/rumours/">
            Rumour register
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
        <div className="card" data-contract="recruitment.transfer-summary">
          <div className="card-head">
            <div>
              <p className="eyebrow">Transfer register</p>
              <h2>What actually happened</h2>
            </div>
          </div>
          <div className="stat-row">
            <StatTile
              label="Registered moves"
              value={transfers?.summary.total ?? 0}
              note={
                transfers
                  ? `${transfers.summary.players} players · ${transfers.summary.period ?? "register"}`
                  : "register"
              }
            />
            <StatTile
              label="Confirmed"
              value={transfers?.summary.confirmed ?? 0}
              note="official announcement"
            />
            <StatTile
              label="Loans out"
              value={transfers?.loan_scope?.register_current.out_count ?? 0}
              note={`${transfers?.loan_scope?.season ?? "current"} register`}
            />
            <StatTile
              label="Loans in"
              value={transfers?.loan_scope?.register_current.in_count ?? 0}
              note="current register"
            />
          </div>
          {transfers ? (
            <p className="fine-print">
              Moves include loans, frees and youth/development registrations, and one
              player can appear more than once (a loan out and a return, for example).
              The register spans {transfers.summary.seasons_covered} seasons and{" "}
              {transfers.summary.windows_covered} windows; {transfers.summary.confirmed}{" "}
              rows carry an official announcement and the rest are curated from the
              provider feed and Wikipedia.
            </p>
          ) : null}
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

        <div className="card" data-contract="recruitment.rumour-summary">
          <div className="card-head">
            <div>
              <p className="eyebrow">Rumour register</p>
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
            Rumour register, profile and fan signal →
          </Link>
        </div>
      </section>

      <section className="section" data-contract="recruitment.rumour-affiliation">
        <div className="card">
          <div className="card-head">
            <div>
              <p className="eyebrow">Affiliation</p>
              <h2>Former players and targets are different lanes</h2>
            </div>
            <Link className="text-link" href="/former-players/">
              Former-player register →
            </Link>
          </div>
          <p>
            The fan signal now separates external targets from current squad, current
            non-official and former players. The target profile counts active incoming
            external links only; a former player linked back is a return link, not a
            normal target.
          </p>
          <div className="stat-row four">
            <StatTile
              label="External targets"
              value={forum?.profile.affiliation_mix?.external_target ?? 0}
              note="fan-signal names"
            />
            <StatTile
              label="Former players"
              value={forum?.profile.affiliation_mix?.former_player ?? 0}
              note="separate lane"
            />
            <StatTile
              label="Current squad"
              value={
                (forum?.profile.affiliation_mix?.current_squad ?? 0) +
                (forum?.profile.affiliation_mix?.loan_out ?? 0) +
                (forum?.profile.affiliation_mix?.current_non_official ?? 0)
              }
              note="not targets"
            />
            <StatTile
              label="Target-profile sample"
              value={profile?.sample_size ?? 0}
              note="active incoming external"
            />
          </div>
        </div>
      </section>

      <section className="section" data-contract="recruitment.profile">
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
              <span className="badge badge-warn" data-contract-indicator="confidence">
                Small sample — treat as a hint, not a target list
              </span>
            ) : null}
          </div>
          <div className="card">
            <BucketBars title="Position mix" buckets={profile?.buckets.position ?? {}} />
          </div>
        </div>
      </section>

      <section className="section" data-contract="recruitment.forum-signals">
        <ForumSignalPanel data={forum} limit={6} showSentiment={false} showTopics={false} />
        <p className="back-link">
          <Link href="/rumours/">All fan signal and the sentiment comparison →</Link>
          {" · "}
          <Link href="/news/">News &amp; rumours, the bridge →</Link>
          {" · "}
          <Link href="/analysis/">Season overview →</Link>
        </p>
      </section>
    </ContractPage>
  );
}
