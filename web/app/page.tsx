import Link from "next/link";
import { CompetitionStrip } from "@/components/CompetitionStrip";
import { ContractPage } from "@/components/ContractPage";
import { FixtureList } from "@/components/FixtureList";
import { FormStrip } from "@/components/FormStrip";
import { LeagueTable } from "@/components/LeagueTable";
import { PlayerLink } from "@/components/PlayerLink";
import { RumourCard } from "@/components/RumourCard";
import { StatTile } from "@/components/StatTile";
import { formatDate } from "@/lib/format";
import {
  getAberdeen,
  getForumSignal,
  getManifest,
  getRumours,
  getSquad,
  getTableFiles,
  getTransfers,
} from "@/lib/data";

export default function HomePage() {
  const manifest = getManifest();
  const tables = getTableFiles();
  const aberdeen = getAberdeen();
  const transfers = getTransfers();
  const rumours = getRumours();
  const forum = getForumSignal();
  const squad = getSquad();
  const season = manifest?.season ?? tables[0]?.season ?? "—";

  if (!tables.length) {
    return (
      <ContractPage surface="home" state="empty">
        <section className="empty-state" data-contract="home.empty">
          <h1>No published data yet</h1>
          <p>
            Run <code>uv run fitba publish</code> to generate the web data, then rebuild.
          </p>
        </section>
      </ContractPage>
    );
  }

  const aberdeenTable = tables.find((table) =>
    table.rows.some((row) => row.team_id === "sco:aberdeen"),
  );
  const summary = aberdeen?.summary;
  const standingsUpdatedAt =
    aberdeenTable?.rows[0]?.updated_at ?? manifest?.generated_at ?? null;
  const latestTransfers = transfers?.transfers.slice(0, 2) ?? [];
  const latestRumours = rumours?.rumours.slice(0, 2) ?? [];
  const topPlayers = (squad?.players ?? [])
    .filter((player) => player.status !== "loan_out" && player.totals)
    .sort((a, b) => (b.totals?.minutes ?? 0) - (a.totals?.minutes ?? 0))
    .slice(0, 6);

  return (
    <ContractPage surface="home">
      <section className="hero" data-contract="home.hero">
        <p className="eyebrow">Season {season}</p>
        <p className="place-line">Aberdeen · North Sea · 1903</p>
        <h1>
          Aberdeen FC,
          <br />
          without the noise.
        </h1>
        <p className="lede">
          An independent, data-driven record of Aberdeen FC — the numbers, the
          sources and the argument, without the hot takes.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/matchday/">
            Matchday
          </Link>
          <Link className="button" href="/recruitment/">
            Off the pitch
          </Link>
          <Link className="button button-ghost" href="/news/">
            News &amp; rumours
          </Link>
          <Link className="button button-ghost" href="/themes/">
            The bigger picture
          </Link>
        </div>
      </section>

      <section className="grid two-col door-grid">
        <div className="card door-card" data-contract="home.matchday">
          <div className="card-head">
            <div>
              <p className="eyebrow">On the pitch</p>
              <h2>Matchday</h2>
            </div>
            <span className="door-number">01</span>
          </div>
          <p>
            The next fixture, both predicted XIs, form and home/away splits,
            opponent style and strength, and the keys to the match. Fixtures,
            results and the full pyramid are one click away.
          </p>

          {summary ? (
            <div className="stat-row">
              <StatTile
                label="Position"
                value={summary.position}
                note={aberdeenTable?.short_name ?? "League"}
              />
              <StatTile label="Points" value={summary.points} note={`${summary.played} played`} />
              <StatTile label="Form" value={<FormStrip form={summary.form} />} />
            </div>
          ) : null}

          <div className="mini-block">
            <p className="eyebrow">Next up</p>
            <FixtureList
              fixtures={aberdeen?.fixtures.slice(0, 2) ?? []}
              empty="No upcoming fixtures."
            />
          </div>

          <div className="door-links">
            <Link href="/fixtures/">Results &amp; fixtures</Link>
            <Link href="/competitions/">Competitions</Link>
            <Link href="/scotland/">The pyramid</Link>
            <Link href="/matchday/">Matchday dashboard</Link>
          </div>
        </div>

        <div className="card door-card" data-contract="home.off-pitch">
          <div className="card-head">
            <div>
              <p className="eyebrow">Off the pitch</p>
              <h2>Recruitment &amp; transfers</h2>
            </div>
            <span className="door-number">02</span>
          </div>
          <p>
            Confirmed transfers and loans, the scouting method, and a curated
            rumour register that turns links and fan chatter into a testable profile.
          </p>

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
              label="Active rumours"
              value={rumours?.summary.by_status.active ?? 0}
              note="curated"
            />
            <StatTile
              label="Fan signals"
              value={forum?.signals.length ?? 0}
              note="names mentioned"
            />
          </div>

          {latestTransfers.length ? (
            <div className="mini-block">
              <p className="eyebrow">Latest confirmed</p>
              <ul className="plain-list">
                {latestTransfers.map((transfer) => (
                  <li key={transfer.transfer_id}>
                    <strong>
                      <PlayerLink name={transfer.player_name} href={transfer.player_href} />
                    </strong>{" "}
                    · {transfer.direction === "in" ? "in" : "out"} ·{" "}
                    {transfer.from_club_name} → {transfer.to_club_name}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="door-links">
            <Link href="/transfers/">Transfers</Link>
            <Link href="/loans/">Loans</Link>
            <Link href="/scouting/">Scouting</Link>
            <Link href="/rumours/">Rumours</Link>
          </div>
        </div>
      </section>

      {squad ? (
        <section className="section squad-bridge" data-contract="home.squad">
          <div className="section-head">
            <div>
              <p className="eyebrow">Squad · the same player across the record</p>
              <h2>The current squad</h2>
            </div>
            <Link className="text-link" href="/squad/">
              Full squad →
            </Link>
          </div>
          <div className="grid two-col">
            <div className="card">
              <p>
                The squad is where Matchday and Off the pitch meet: the same
                player appears in the table, the transfer register and the rumour
                mill. Every current player has a profile with current-season
                output, and loanees are tagged with their loan club.
              </p>
              <div className="stat-row">
                <StatTile label="Squad" value={squad.summary.squad_size} note="registered" />
                <StatTile label="On loan" value={squad.summary.loans_out} note="tagged" />
                <StatTile
                  label="Average age"
                  value={squad.summary.average_age ?? "—"}
                  note="registered squad"
                />
                <StatTile
                  label="Stats unavailable"
                  value={squad.summary.stats_unavailable}
                  note="labelled"
                  indicator="unknown"
                />
              </div>
              <Link className="text-link" href="/squad/">
                Squad, loans and coverage →
              </Link>
            </div>
            <div className="card">
              <p className="eyebrow">Most minutes</p>
              <h3>Current-season leaders</h3>
              {topPlayers.length ? (
                <ul className="signal-list">
                  {topPlayers.map((player) => (
                    <li key={player.player_id}>
                      <PlayerLink name={player.full_name || player.name} href={player.href} />
                      <span className="muted">
                        {player.position_group ?? "—"} · {player.totals?.minutes ?? 0} mins
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted">No player minutes published yet.</p>
              )}
              <p className="fine-print">
                A player link opens the same profile wherever the player is
                mentioned across the site.
              </p>
            </div>
          </div>
        </section>
      ) : null}

      <section className="section bridge-band" data-contract="home.news-rumours">
        <div className="section-head">
          <div>
            <p className="eyebrow">News, rumours and fan signal</p>
            <h2>News &amp; rumours</h2>
          </div>
          <Link className="text-link" href="/news/">
            All news &amp; rumours →
          </Link>
        </div>
        <div className="grid three-col">
          <div className="card">
            <p className="eyebrow">Official · low frequency</p>
            <h3>From Pittodrie</h3>
            {aberdeen?.news.length ? (
              <ul className="plain-list">
                {aberdeen.news.slice(0, 3).map((article) => (
                  <li key={article.article_id}>
                    <a href={article.url} target="_blank" rel="noreferrer">
                      {article.title}
                    </a>
                    <span className="muted">
                      {" "}
                      ·{" "}
                      {article.published_date
                        ? formatDate(article.published_date)
                        : article.category}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No official articles ingested yet.</p>
            )}
          </div>
          <div className="card">
            <p className="eyebrow">Curated · sourced</p>
            <h3>Rumour register</h3>
            {latestRumours.length ? (
              <div className="rumour-grid">
                {latestRumours.map((rumour) => (
                  <RumourCard key={rumour.rumour_id} rumour={rumour} />
                ))}
              </div>
            ) : (
              <p className="muted">
                No curated links yet. The register stays empty until a link has a
                public source.
              </p>
            )}
            <Link className="text-link" href="/rumours/">
              Rumour register →
            </Link>
          </div>
          <div className="card">
            <p className="eyebrow">Fan signal · reference use</p>
            <h3>What the forum is saying</h3>
            {forum?.signals.length ? (
              <ul className="signal-list">
                {forum.signals.slice(0, 5).map((signal) => (
                  <li key={`${signal.player_name}-${signal.player_key ?? ""}`}>
                    <PlayerLink name={signal.player_name} href={signal.player_href} />
                    <span className="muted">
                      {signal.mentions} mention{signal.mentions === 1 ? "" : "s"}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No fan signal ingested yet.</p>
            )}
            <p className="fine-print">
              Mention counts, not transfer links. No raw posts are published.
            </p>
            <Link className="text-link" href="/rumours/">
              Fan signal &amp; sentiment →
            </Link>
          </div>
        </div>
      </section>

      <p className="back-link">
        <Link href="/history/">
          The Cormack era: the record behind the strategy →
        </Link>
      </p>

      {aberdeen ? (
        <section className="section" data-contract="home.competitions">
          <div className="section-head">
            <div>
              <p className="eyebrow">Aberdeen</p>
              <h2>Current competitions</h2>
            </div>
            <Link className="text-link" href="/fixtures/">
              Results &amp; fixtures →
            </Link>
          </div>
          <CompetitionStrip competitions={aberdeen.competitions} />
        </section>
      ) : null}

      {aberdeenTable ? (
        <section className="section" data-contract="home.standings">
          <div className="section-head">
            <div>
              <p className="eyebrow">{aberdeenTable.short_name}</p>
              <h2>Current standings</h2>
            </div>
            <Link className="text-link" href="/matchday/">
              Matchday hub →
            </Link>
          </div>
          <LeagueTable
            rows={aberdeenTable.rows}
            highlightTeamId="sco:aberdeen"
            cutoffs={aberdeenTable.cutoffs}
          />
          <p className="fine-print" data-contract-indicator="source">
            Computed from league results
            {standingsUpdatedAt
              ? ` · updated ${formatDate(String(standingsUpdatedAt).slice(0, 10))}`
              : ""}
            .
          </p>
          {aberdeenTable.qualification_note ? (
            <p className="fine-print">{aberdeenTable.qualification_note}</p>
          ) : null}
        </section>
      ) : null}
    </ContractPage>
  );
}
