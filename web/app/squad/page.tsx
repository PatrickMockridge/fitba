import Link from "next/link";
import { BucketBars } from "@/components/BucketBars";
import { ContractPage } from "@/components/ContractPage";
import { SquadBoard } from "@/components/SquadBoard";
import { StatTile } from "@/components/StatTile";
import { getSquad } from "@/lib/data";

export const metadata = { title: "Current squad · fitba" };

const GROUP_LABELS: Record<string, string> = {
  goalkeeper: "Goalkeeper",
  defender: "Defender",
  midfielder: "Midfielder",
  attacker: "Attacker",
  unknown: "No role observed",
};

function groupBuckets(buckets: Record<string, number>): Record<string, number> {
  return Object.fromEntries(
    Object.entries(buckets).map(([key, value]) => [GROUP_LABELS[key] ?? key, value]),
  );
}

export default function SquadPage() {
  const squad = getSquad();
  if (!squad || !squad.players.length) {
    return (
      <ContractPage surface="squad" state="empty">
        <section className="empty-state" data-contract="squad.empty">
          <h1>No squad published</h1>
          <p>
            Run <code>uv run fitba squad</code> and then{" "}
            <code>uv run fitba publish</code> to ingest the current squad and
            current-season statistics.
          </p>
        </section>
      </ContractPage>
    );
  }

  return (
    <ContractPage surface="squad">
      <section className="page-head" data-contract="squad.hero">
        <p className="eyebrow">On-field · Season {squad.season}</p>
        <h1>The current squad</h1>
        <p className="lede">
          Every Aberdeen player in one place: the men on the pitch, the players
          out on loan, and the current-season output the licensed feed can
          support. The same player appears in the matchday XI, the transfer
          register and this squad record.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/matchday/">
            Matchday
          </Link>
          <Link className="button" href="/recruitment/">
            Off the pitch
          </Link>
          <Link className="button button-ghost" href="/transfers/">
            Confirmed business
          </Link>
          <span className="badge badge-neutral">
            Role grid: {squad.role_meta.fixtures_with_grid}/{squad.role_meta.fixtures_total} matches
          </span>
        </div>
      </section>

      <div className="stat-row four" data-contract="squad.summary">
        <StatTile label="Squad" value={squad.summary.squad_size} note="registered players" />
        <StatTile
          label="On loan out"
          value={squad.summary.loans_out}
          note={squad.summary.loans_in ? `${squad.summary.loans_in} loaned in` : "tagged below"}
        />
        <StatTile
          label="Role evidence"
          value={squad.summary.roles_observed + squad.summary.roles_partial}
          note={`${squad.summary.roles_unknown} without a role, incl. ${squad.summary.loans_out} loanees out`}
        />
        <StatTile
          label="Stats unavailable"
          value={squad.summary.stats_unavailable}
          note="labelled, not zero-filled"
          indicator="unknown"
        />
      </div>

      <section className="section" data-contract="squad.roster">
        <div className="section-head">
          <div>
            <p className="eyebrow">Squad and loans</p>
            <h2>Players and current-season output</h2>
          </div>
          <Link className="text-link" href="/loans/">
            Loan register →
          </Link>
        </div>
        <SquadBoard players={squad.players} />
        <p className="fine-print" data-contract="squad.coverage">
          {squad.coverage.note} Loan tags come from the confirmed transfer
          register; a loanee&apos;s parent-club rows are never shown as loan-club
          output.
        </p>
      </section>

      <div className="grid two-col">
        <section className="card" data-contract="squad.role-mix">
          <p className="eyebrow">Shape</p>
          <h2>Role mix</h2>
          <BucketBars
            title="Registered squad by primary position group"
            buckets={groupBuckets(squad.summary.by_primary_group)}
          />
          <p className="fine-print">
            Primary group only; the filter above uses the full eligibility set,
            so a full-back or wing-back can appear under both defenders and
            midfielders. Registered squad only; the {squad.summary.loans_out}{" "}
            loanees out are excluded because loan-club lineups are not ingested.
            Positions come from the starting-XI formation grid. A player with no
            role evidence is shown separately rather than forced into a generic
            defender or midfielder bucket. The two early League Cup matches had
            no formation grid and are reported in the coverage note, not guessed.
          </p>
        </section>
        <section className="card" data-contract="squad.how-to">
          <p className="eyebrow">How to read the page</p>
          <h2>What is measured and what is missing</h2>
          <ul className="plain-list">
            <li>
              <strong>Available:</strong> the licensed feed has current-season
              rows for the player at Aberdeen or at the loan club.
            </li>
            <li>
              <strong>Unavailable:</strong> no current-season rows for the
              relevant club. The page says so rather than showing zeroes.
            </li>
            <li>
              <strong>On loan:</strong> the tag comes from the confirmed
              register. Loan-club stats are used when the feed covers that club;
              otherwise the loan-club section is explicitly unavailable.
            </li>
            <li>
              <strong>Position:</strong> the starting-XI formation grid gives
              FM-style position slots, not one label. A full-back / wing-back is
              one slot and counts as both a defender and a midfielder; a DM is a
              midfielder; a winger is an attacker. The Group and Side filters
              use every eligible slot. A stretch slot is a low-evidence
              emergency option, not a new primary. No role is inferred from
              foot, shirt number or a substitute&apos;s entry.
            </li>
            <li>
              <strong>Starts and substitutions:</strong> starts, substitute
              appearances and on-pitch minutes are reconstructed from lineups and
              substitution events, so the split is visible. Provider per-match
              time fields are not used as the headline.
            </li>
            <li>
              <strong>Position stats:</strong> for goalkeepers and defensive
              roles, goals conceded while on the pitch, clean sheets and own goals
              come before goals and assists. Midfielders lead with goals, assists
              and key passes; wide players and forwards lead with goals, assists
              and shots. Position context is reconstructed from fixture lineups
              and events.
            </li>
            <li>
              <strong>Foot:</strong> preferred foot is the one field the team
              sheet does not contain. It is on the player profile only, with its
              source or an explicit unknown; it is never inferred from role or
              side.
            </li>
            <li>
              <strong>Cards:</strong> the yellow and red card marks sit in the
              column headings; the row cells are counts. Red includes second
              yellows.
            </li>
            <li>
              <strong>Links:</strong> current players link to their profile
              everywhere on the site. Former players and rumour targets do not.
            </li>
          </ul>
          <Link
            className="text-link"
            href="/methodology/"
            data-contract-indicator="source"
          >
            Method and source policy →
          </Link>
        </section>
      </div>

      <p className="back-link">
        <Link href="/matchday/">← Matchday</Link>
        {" · "}
        <Link href="/analysis/">Data analysis →</Link>
        {" · "}
        <Link href="/recruitment/">Off the pitch →</Link>
      </p>
    </ContractPage>
  );
}
