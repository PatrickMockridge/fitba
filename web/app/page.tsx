import Link from "next/link";
import { FormStrip } from "@/components/FormStrip";
import { LeagueTable } from "@/components/LeagueTable";
import { StatTile } from "@/components/StatTile";
import { getAberdeen, getManifest, getTableFiles } from "@/lib/data";

export default function HomePage() {
  const manifest = getManifest();
  const tables = getTableFiles();
  const aberdeen = getAberdeen();
  const season = manifest?.season ?? tables[0]?.season ?? "—";

  if (!tables.length) {
    return (
      <section className="empty-state">
        <h1>No published data yet</h1>
        <p>
          Run <code>uv run fitba publish</code> to generate the web data, then rebuild.
        </p>
      </section>
    );
  }

  const premiership = tables.find((table) => table.competition_id === "sco:premiership");
  const summary = aberdeen?.summary;
  const recent = aberdeen?.results.slice(0, 4) ?? [];

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Season {season}</p>
        <h1>
          The Scottish pyramid,
          <br />
          from Pittodrie out.
        </h1>
        <p className="lede">
          Results and tables for all four SPFL tiers, with Aberdeen as the focal club —
          and a scouting and loans layer being built on top.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/scotland/premiership/">
            Premiership table
          </Link>
          <Link className="button button-ghost" href="/clubs/aberdeen/">
            Aberdeen dashboard
          </Link>
        </div>
      </section>

      <section className="grid two-col">
        <div className="card aberdeen-card">
          <div className="card-head">
            <div>
              <p className="eyebrow">Focal club</p>
              <h2>Aberdeen</h2>
            </div>
            <span className="club-roundel">AFC</span>
          </div>
          {summary ? (
            <>
              <div className="stat-row">
                <StatTile label="Position" value={summary.position} note="Premiership" />
                <StatTile label="Points" value={summary.points} note={`${summary.played} played`} />
                <StatTile
                  label="Goal difference"
                  value={summary.gd > 0 ? `+${summary.gd}` : summary.gd}
                  note={`${summary.gf} for · ${summary.ga} against`}
                />
                <StatTile label="Form" value={<FormStrip form={summary.form} />} />
              </div>
              <ul className="result-list">
                {recent.map((match) => (
                  <li key={match.match_id}>
                    <span className={`result-dot result-${match.result.toLowerCase()}`}>
                      {match.result}
                    </span>
                    <span className="result-venue">{match.venue}</span>
                    <span className="result-opponent">{match.opponent_name}</span>
                    <span className="result-score">
                      {match.goals_for}–{match.goals_against}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="muted">No current-season row yet.</p>
          )}
          <Link className="text-link" href="/clubs/aberdeen/">
            Full Aberdeen dashboard →
          </Link>
        </div>

        <div className="card">
          <div className="card-head">
            <div>
              <p className="eyebrow">The pyramid</p>
              <h2>Four tiers, one view</h2>
            </div>
          </div>
          <div className="tier-list">
            {tables.map((table) => {
              const slug = table.competition_id.split(":")[1];
              const leader = table.rows[0];
              return (
                <Link className="tier-row" key={table.competition_id} href={`/scotland/${slug}/`}>
                  <span>
                    <strong>{table.short_name}</strong>
                    <small>{table.rows.length} clubs</small>
                  </span>
                  <span className="tier-leader">
                    {leader ? `${leader.team_name} · ${leader.points} pts` : "—"}
                  </span>
                </Link>
              );
            })}
          </div>
          <Link className="text-link" href="/scotland/">
            All tables →
          </Link>
        </div>
      </section>

      {premiership ? (
        <section className="section">
          <div className="section-head">
            <div>
              <p className="eyebrow">Premiership</p>
              <h2>Current standings</h2>
            </div>
            <Link className="text-link" href="/scotland/premiership/">
              Full table →
            </Link>
          </div>
          <LeagueTable rows={premiership.rows.slice(0, 6)} highlightTeamId="sco:aberdeen" compact />
        </section>
      ) : null}

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">In build</p>
            <h2>The next layers</h2>
          </div>
        </div>
        <div className="grid three-col">
          <Link className="card feature-card" href="/scouting/">
            <span className="feature-index">01</span>
            <h3>Recruitment board</h3>
            <p>
              Position-adjusted percentiles, Aberdeen style fit and budget bands across
              Scotland and a European pool — starting with verified data only.
            </p>
            <span className="status-line">Schema and method published · data pending</span>
          </Link>
          <Link className="card feature-card" href="/loans/">
            <span className="feature-index">02</span>
            <h3>Loanee tracker</h3>
            <p>
              Aberdeen players out on loan, with minutes and output labelled by coverage —
              including curated League One/Two records where rich data does not exist.
            </p>
            <span className="status-line">Register ready · first entries pending</span>
          </Link>
          <div className="card feature-card">
            <span className="feature-index">03</span>
            <h3>2D match viewer</h3>
            <p>
              Goals and key passages as an event-reconstructed 2D animation. Player tokens
              and the ball on a 105×68 pitch, never presented as tracking data.
            </p>
            <span className="status-line">Event layer pending · design fixed</span>
          </div>
        </div>
      </section>
    </>
  );
}
