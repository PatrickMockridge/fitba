import Link from "next/link";
import { CompetitionStrip } from "@/components/CompetitionStrip";
import { FixtureList } from "@/components/FixtureList";
import { formatDate, getAberdeen, getManifest } from "@/lib/data";

export const metadata = { title: "Results & fixtures · fitba" };

export default function FixturesPage() {
  const aberdeen = getAberdeen();
  const manifest = getManifest();
  if (!aberdeen) {
    return (
      <section className="empty-state">
        <h1>No fixtures published</h1>
        <p>Run <code>uv run fitba fixtures</code> and then republish.</p>
      </section>
    );
  }

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Aberdeen · Season {aberdeen.season}</p>
        <h1>Results &amp; fixtures</h1>
        <p className="lede">
          All three Scottish competitions in one place:{" "}
          {aberdeen.summary?.competition_name ?? "the league"}, the Premier Sports
          Cup and the Scottish Cup. League results and team stats come from
          Football-Data.co.uk; League Cup and Scottish Cup fixtures come from
          API-Football; Aberdeen club fixtures come from the SPFL feed. The
          Scottish Cup feed is partial and missing rounds are labelled.
        </p>
        {manifest ? (
          <span className="badge badge-neutral">Data as of {formatDate(manifest.generated_at.slice(0, 10))}</span>
        ) : null}
      </section>

      <CompetitionStrip competitions={aberdeen.competitions} />

      <div className="grid two-col">
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Upcoming</p>
              <h2>Next up</h2>
            </div>
          </div>
          <FixtureList fixtures={aberdeen.fixtures} empty="No upcoming fixtures." />
        </section>

        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Played</p>
              <h2>Recent results</h2>
            </div>
          </div>
          <FixtureList
            fixtures={aberdeen.recent_results}
            showResult
            empty="No recent results."
          />
        </section>
      </div>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Competition detail</p>
            <h2>What Aberdeen are in</h2>
          </div>
        </div>
        <ul className="plain-list">
          {aberdeen.competitions.map((competition) => (
            <li key={competition.id}>
              <strong>{competition.name}</strong> — {competition.stage ?? competition.status}
              {competition.next_fixture
                ? ` · ${competition.next_fixture.venue === "H" ? "v" : "at"} ${
                    competition.next_fixture.opponent_name
                  }, ${formatDate(competition.next_fixture.date)}${
                    competition.next_fixture.kickoff
                      ? `, ${competition.next_fixture.kickoff}`
                      : ""
                  }`
                : competition.entry_round && competition.entry_date
                  ? ` · ${competition.entry_round}, ${formatDate(competition.entry_date)}`
                  : ""}
              {competition.note ? (
                <span className="fine-print"> {competition.note}</span>
              ) : null}
            </li>
          ))}
        </ul>
        <p className="fine-print">
          The daily pipeline refreshes the SPFL feed. The Scottish Cup draw is added
          when the SFA publishes the fourth-round fixtures.
        </p>
        <Link className="text-link" href="/matchday/">
          Matchday dashboard →
        </Link>{" "}
        <Link className="text-link" href="/matches/">
          Match record →
        </Link>
      </section>
    </>
  );
}
