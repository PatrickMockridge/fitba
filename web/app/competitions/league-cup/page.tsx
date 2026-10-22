import Link from "next/link";
import { CupGroupTable } from "@/components/CupGroupTable";
import { CupRound } from "@/components/CupRound";
import { formatDate, getLeagueCup } from "@/lib/data";

export const metadata = { title: "League Cup · fitba" };

export default function LeagueCupPage() {
  const cup = getLeagueCup();
  if (!cup) {
    return (
      <section className="empty-state">
        <h1>No League Cup data</h1>
        <p>Run <code>uv run fitba cups</code> and <code>uv run fitba publish</code>.</p>
      </section>
    );
  }

  const knockout = cup.rounds.filter((round) => round.name !== "Group Stage");
  const qualifierGroups = [
    {
      title: "Group winners",
      rows: cup.qualifiers.group_winners.map((row) => ({
        name: row.team_name,
        note: `${row.group} · ${row.points} pts`,
      })),
    },
    {
      title: "Best runners-up",
      rows: cup.qualifiers.best_runners_up.map((row) => ({
        name: row.team_name,
        note: `${row.group} · ${row.points} pts`,
      })),
    },
    {
      title: "European byes",
      rows: cup.qualifiers.byes.map((row) => ({ name: row.team_name, note: "Bye to last 16" })),
    },
  ];

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Cup · Season {cup.season}</p>
        <h1>{cup.name}</h1>
        <p className="lede">
          Eight groups of five, then a single-leg knockout. The five European
          representatives join in the last 16 alongside the eight group winners
          and the three best runners-up. Group games are decided by a shoot-out
          if level.
        </p>
        <div className="hero-actions">
          <Link className="button button-ghost" href="/competitions/">
            All competitions
          </Link>
          <Link className="button button-ghost" href="/sources/">
            Source coverage
          </Link>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <p className="eyebrow">Format</p>
            <h2>Where the clubs enter</h2>
          </div>
          <span className="badge badge-neutral">Official 2026/27</span>
        </div>
        <ul className="plain-list">
          <li>
            <strong>Group stage:</strong> 8 groups of 5 — 37 non-European SPFL
            clubs plus Linlithgow Rose, Brora Rangers and Brechin City.
          </li>
          <li>
            <strong>Byes:</strong> Celtic, Hearts, Rangers, Motherwell and
            Hibernian — the five European representatives — enter in the last 16.
          </li>
          <li>
            <strong>Qualification:</strong> 8 group winners + 3 best runners-up
            join the five byes for a 16-team second round.
          </li>
          <li>
            <strong>Points:</strong> 3 for a win; 1 for a draw plus a shoot-out
            bonus. Tables show W / PW / PL / L, not a flat W/D/L.
          </li>
          <li>
            <strong>Knockout:</strong> single-leg, extra time and penalties.
          </li>
        </ul>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Status</p>
            <h2>{cup.status.phase}</h2>
          </div>
          <span className="badge badge-ok">In progress</span>
        </div>
        <div className="grid two-col">
          {cup.status.next_fixtures.map((fixture) => (
            <div className="card" key={fixture.match_id}>
              <p className="eyebrow">{fixture.round} · {formatDate(fixture.date)}</p>
              <h3>
                {fixture.home_team_name} v {fixture.away_team_name}
              </h3>
              <p className="fine-print">
                {fixture.kickoff ?? "TBC"}
                {fixture.venue ? ` · ${fixture.venue}` : ""}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Group stage</p>
            <h2>Eight groups</h2>
          </div>
          <span className="badge badge-neutral">Computed from 80 fixtures</span>
        </div>
        <p className="fine-print">
          Group positions are computed from the group fixtures. The licensed feed
          does not expose the official draw letters, so the app assigns A–H from
          the fixture graph; the table contents are group-correct.
        </p>
        <div className="grid two-col">
          {cup.groups.map((group) => (
            <div className="card" key={group.id}>
              <CupGroupTable group={group} highlightTeamId="sco:aberdeen" />
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Qualifiers</p>
            <h2>Who reached the last 16</h2>
          </div>
          <span className="badge badge-ok">{cup.qualifiers.count} of 16</span>
        </div>
        <div className="cup-qualifiers">
          {qualifierGroups.map((group) => (
            <div className="card" key={group.title}>
              <h3>{group.title}</h3>
              <ul className="plain-list">
                {group.rows.map((row) => (
                  <li key={`${group.title}-${row.name}`}>
                    <strong>{row.name}</strong>
                    <span className="muted"> · {row.note}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Knockout</p>
            <h2>From 16 to the final</h2>
          </div>
        </div>
        <div className="pyramid-stack">
          {knockout.map((round) => (
            <div className="card" key={round.name}>
              <CupRound round={round} highlightTeamId="sco:aberdeen" />
            </div>
          ))}
        </div>
      </section>

      <p className="fine-print">
        Source: {cup.source.name}, checked {cup.source.verified_at ?? "—"}. Group
        tables and group letters are computed by the app; the licensed feed
        supplies the fixtures and penalty scores but not standings.
      </p>
      <Link className="text-link" href="/competitions/">
        ← All competitions
      </Link>
    </>
  );
}
