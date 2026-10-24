import Link from "next/link";
import { BucketBars } from "@/components/BucketBars";
import { ContractPage } from "@/components/ContractPage";
import { SquadBoard } from "@/components/SquadBoard";
import { StatTile } from "@/components/StatTile";
import { getSquad } from "@/lib/data";
import { FAMILY_LABELS } from "@/lib/roles";
import { formatDate } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/squad/" }, title: "Current squad · fitba" };

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

function familyBuckets(buckets: Record<string, number>): Record<string, number> {
  return Object.fromEntries(
    Object.entries(buckets).map(([key, value]) => [FAMILY_LABELS[key] ?? key, value]),
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
        <p className="fine-print" data-contract="squad.source">
          Canonical roster:{" "}
          <a
            className="text-link"
            href={squad.roster_meta?.source_url ?? "https://www.afc.co.uk/en/teams/mens"}
            rel="noreferrer"
          >
            Aberdeen FC men&apos;s team
          </a>
          {squad.roster_meta?.fetched_at
            ? ` · checked ${formatDate(squad.roster_meta.fetched_at)}`
            : " · official list unavailable; using the API-Football snapshot with a visible fallback"}
          . Inclusion, section, order and shirt number come from the official
          page; API-Football supplies statistics and identity. Rows not on the
          official list are not squad players.
        </p>
      </section>

      <div className="stat-row four" data-contract="squad.summary">
        <StatTile
          label="Squad"
          value={squad.summary.official_squad_size ?? squad.summary.squad_size}
          note={`official list; ${squad.summary.excluded_api ?? 0} API-only rows excluded`}
        />
        <StatTile
          label="On loan out"
          value={squad.summary.loans_out}
          note={
            squad.loan_scope
              ? `official list; ${squad.loan_scope.register_current.out_count} in the 2026-27 register`
              : squad.summary.loans_in
                ? `${squad.summary.loans_in} loaned in`
                : "official list"
          }
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
          {squad.coverage.note} Loan tags come from the official roster section
          and the confirmed transfer register; a loanee&apos;s parent-club rows
          are never shown as loan-club output. The table follows the official
          section order; API-only rows outside that list are excluded from the
          squad and its counts.
        </p>
        {squad.roster_only?.length ? (
          <div className="mini-block" data-contract="squad.roster-only">
            <p className="eyebrow">Official list only</p>
            <p className="fine-print">
              The official page lists these players, but no unique API-Football
              player id was found. They are shown here rather than dropped.
            </p>
            <ul className="plain-list">
              {squad.roster_only.map((player) => (
                <li key={`${player.name}-${player.number}`}>
                  {player.name ?? "Unknown"} · {player.position ?? "position unknown"}
                  {player.number ? ` · ${player.number}` : ""}
                  {player.official_href ? (
                    <>
                      {" "}
                      <a
                        className="text-link"
                        href={`https://www.afc.co.uk${player.official_href}`}
                        rel="noreferrer"
                      >
                        official profile
                      </a>
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <div className="grid two-col">
        <section className="card" data-contract="squad.role-mix">
          <p className="eyebrow">Shape</p>
          <h2>Role mix and squad profile</h2>
          <div className="stat-row four">
            <StatTile
              label="Average age"
              value={squad.summary.average_age ?? "—"}
              note="all players"
            />
            <StatTile
              label="Registered"
              value={squad.summary.squad_size}
              note={`${squad.summary.loans_out} loaned out`}
            />
            <StatTile
              label="Role evidence (all)"
              value={squad.summary.roles_observed + squad.summary.roles_partial}
              note={`${squad.summary.roles_unknown} unknown, incl. ${squad.summary.loans_out} loanees out`}
            />
            <StatTile
              label="Starts with a role"
              value={`${squad.role_meta.starts_with_role}/${squad.role_meta.starts_total}`}
              note={`${squad.role_meta.role_coverage} coverage`}
            />
          </div>
          <BucketBars
            title="Registered squad by primary position group"
            buckets={groupBuckets(squad.summary.by_primary_group_squad)}
            absolute
          />
          <BucketBars
            title="Registered squad by primary role family"
            buckets={familyBuckets(squad.summary.by_role_family_squad)}
            absolute
          />
          <p className="fine-print">
            Primary group and role family come from the starting-XI grid. Primary
            group counts each player once by the first broad group of their primary
            slot; the filter above uses every eligible slot, so a full-back can
            appear under both defender and midfielder. Registered squad only; the{" "}
            {squad.summary.loans_out} loanees out are excluded because loan-club
            lineups are not ingested. No role evidence is shown as unknown, not
            forced into a bucket.
          </p>
        </section>
        <section className="card" data-contract="squad.how-to">
          <p className="eyebrow">How to read the page</p>
          <h2>What is measured and what is missing</h2>
          <div className="table-wrap">
            <table className="league-table compact">
              <caption className="fine-print">
                Data classes on this page, what they show and how missing values
                are labelled.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Class</th>
                  <th scope="col">What is shown</th>
                  <th scope="col">Missing state</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="strong">Current-season output</td>
                  <td>Provider rows for Aberdeen or the loan club.</td>
                  <td>Unavailable, never zero.</td>
                </tr>
                <tr>
                  <td className="strong">Position and role</td>
                  <td>
                    Starting-XI grid, multi-position eligibility, and
                    primary/secondary/stretch slots.
                  </td>
                  <td>
                    Unknown when no grid or formation; never inferred from foot,
                    shirt number or the bench.
                  </td>
                </tr>
                <tr>
                  <td className="strong">Minutes</td>
                  <td>
                    Starts, substitute appearances and on-pitch minutes from
                    lineups and substitution events.
                  </td>
                  <td>
                    Provider per-match time is not used as the headline.
                  </td>
                </tr>
                <tr>
                  <td className="strong">Loan status</td>
                  <td>Loan tag from the confirmed transfer register.</td>
                  <td>
                    Loan-club stats only where the feed covers that club.
                  </td>
                </tr>
                <tr>
                  <td className="strong">Context and links</td>
                  <td>
                    Defensive position stats, provider cards, preferred foot on
                    the player profile, and profile links for current players.
                  </td>
                  <td>
                    Foot is sourced or explicitly unknown; former players link
                    to the former-player register, while rumour targets stay
                    plain text.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
        <Link href="/analysis/">Season overview →</Link>
        {" · "}
        <Link href="/recruitment/">Off the pitch →</Link>
        {" · "}
        <Link href="/former-players/">Former players →</Link>
      </p>
    </ContractPage>
  );
}
