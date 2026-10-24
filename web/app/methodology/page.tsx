import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { getManifest } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/methodology/" }, title: "Method and sources · fitba" };

export default function MethodologyPage() {
  const manifest = getManifest();
  const sources = manifest?.sources ?? [];
  if (!manifest) {
    return (
      <ContractPage surface="methodology" state="empty">
        <section className="empty-state" data-contract="methodology.empty">
          <h1>No methodology data published</h1>
          <p>
            Run <code>uv run fitba publish</code> to build the manifest and the
            source registry.
          </p>
        </section>
      </ContractPage>
    );
  }
  return (
    <ContractPage surface="methodology">
      <section className="page-head" data-contract="methodology.hero">
        <p className="eyebrow">Method</p>
        <h1>How this is built</h1>
        <p className="lede">
          A results-first foundation, then a carefully labelled player layer. The guiding
          rule is simple: never present a derived or curated number as if it were measured
          event data. The product principles live in{" "}
          <Link href="/about/">About</Link>; the licence and coverage record lives in{" "}
          <Link href="/sources/">Sources</Link>.
        </p>
        <div className="hero-actions">
          <Link className="button button-ghost" href="/about/">
            Product principles
          </Link>
          <Link className="button button-ghost" href="/metrics/">
            Metrics &amp; audit
          </Link>
          <Link className="button button-ghost" href="/sources/">
            Sources &amp; licences
          </Link>
        </div>
      </section>

      <section className="card" data-contract="methodology.sources">
        <div className="section-head">
          <div>
            <p className="eyebrow">Sources</p>
            <h2>What feeds the app</h2>
          </div>
          <span className="badge badge-neutral">Schema {manifest?.schema_version ?? "—"}</span>
        </div>
        <div className="table-wrap">
          <table className="league-table">
<caption className="fine-print">Sources, definitions and method notes.</caption>
            <thead>
              <tr>
                <th>Source</th>
                <th>Publication lane</th>
                <th className="num">Rows</th>
                <th>Last checked</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>{source.name}</td>
                  <td>
                    <code>{source.lane}</code>
                  </td>
                  <td className="num">{source.rows.toLocaleString("en-GB")}</td>
                  <td>{source.last_verified ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print" data-contract-indicator="source">
          League results and team match stats come from Football-Data.co.uk and
          are labelled as such; the current-season API-Football migration is
          gated on a full results-and-stats coverage probe. League Cup and
          Scottish Cup fixtures, lineups/roles, player match stats and the squad
          come from API-Football. Aberdeen club fixtures come from the SPFL feed.
          Availability is curated official AFC team news; the provider injury
          snapshot is optional and labelled separately. See{" "}
          <Link href="/sources/">Sources</Link> for the layer truth table. Raw
          payloads are never committed; the app publishes derived tables,
          fixtures and listing metadata with attribution.
        </p>
      </section>

      <div className="grid two-col">
        <section className="card" data-contract="methodology.tables">
          <p className="eyebrow">Tables</p>
          <h2>Computed, not scraped</h2>
          <p>
            Points are 3W + D, goal difference and goals scored break ties, then a
            head-to-head mini-league. Playoff matches are excluded. Points deductions are
            stored in <code>reference/disciplinary.yaml</code> with a citation and applied
            before ranking; the raw and adjusted points are both retained.
          </p>
        </section>
        <section className="card" data-contract="methodology.cutoffs">
          <p className="eyebrow">Cut-offs</p>
          <h2>What the lines mean</h2>
          <p>
            The Premiership splits after 33 matches: 1st–6th contest the title and Europe,
            7th–12th cannot finish higher than 7th. 11th enters the relegation play-off and
            12th is relegated. European places use Scotland&apos;s 2027/28 access list —
            four berths, with the Scottish Cup winner&apos;s route able to move the league
            cut-off. The League Cup carries no European place. Checked 2026-10-21; subject
            to the final UEFA access list and cup outcomes.
          </p>
          <p>
            Below the Premiership, 1st is promoted automatically and 2nd–4th enter the
            promotion play-off. In the Championship and League One, 9th enters the
            relegation play-off and 10th is relegated. In League Two, 10th enters the
            pyramid play-off against the winner of the Highland / Lowland East / Lowland
            West champions&apos; group rather than being relegated automatically.
          </p>
        </section>
        <section className="card" data-contract="methodology.cups">
          <p className="eyebrow">Cup formats</p>
          <h2>League Cup and Scottish Cup</h2>
          <p>
            The League Cup has 8 groups of 5; the five European representatives —
            Celtic, Hearts, Rangers, Motherwell and Hibernian — join in the knockout
            stage, along with 8 group winners and the 3 best runners-up. Group points
            are 3 for a win, 1 for a draw plus a shoot-out bonus. The Scottish Cup is
            a pure knockout of 137 clubs and 136 ties; Aberdeen enter in the fourth
            round on 16 January 2027. Group tables are computed from fixtures, and an
            unpublished draw is shown as awaiting draw.
          </p>
          <p className="fine-print">
            Checked 2026-10-21. The official rule is five European representatives,
            not the top six. Sources: SPFL League Cup format and SFA Scottish Cup
            format and rules. The licensed Scottish Cup feed currently covers the
            First and Second Round only (50 of 136 ties); missing rounds are
            labelled, not invented.
          </p>
        </section>
        <section className="card" data-contract="methodology.assumptions">
          <p className="eyebrow">Uncertainty</p>
          <h2>Assumptions are labelled</h2>
          <p data-contract-indicator="unknown">
            League-strength adjustment uses Elo where available and a documented prior
            otherwise, with a confidence flag and sensitivity check. Budget fit is fee-only
            until a ceiling is set; individual Scottish wages are not public and are never
            invented.
          </p>
        </section>
        <section className="card" data-contract="methodology.coverage">
          <p className="eyebrow">Coverage</p>
          <h2>Event, match, curated, value-only</h2>
          <p>
            Every league and player carries a coverage tier. League One/Two player data is
            curated because no free rich feed exists; the card says so. A value-only player
            is never ranked against event-data peers without a warning.
          </p>
        </section>
        <section className="card" data-contract="methodology.reconstruction">
          <p className="eyebrow">2D viewer</p>
          <h2>Reconstructed, not tracked</h2>
          <p>
            Goals and key passages are rebuilt from event coordinates. Only the ball and
            the players involved in each event are placed from source coordinates; other
            tokens are inferred from formation and average position. Every sequence will
            carry an “event-reconstructed — not tracking data” badge.
          </p>
        </section>
      </div>

      <section className="card" data-contract="methodology.matchday">
        <div className="section-head">
          <div>
            <p className="eyebrow">Matchday</p>
            <h2>Predicted, not team news</h2>
          </div>
          <span className="badge badge-neutral">Projection</span>
        </div>
        <p>
          The next-fixture page projects both XIs from observed formations,
          starts, minutes and role fit, with 4–6 contenders. The style lean uses
          measured shot volume, shot share, shots on target and goals; possession
          is unknown and is not used. Form is league-only, and home/away splits
          use every league match. A missing formation or a small lineup sample is
          labelled unavailable rather than guessed.
        </p>
        <p className="fine-print">
          The opponent refresh is bounded to the next fixture and cache-first. A
          failed refresh carries the previous snapshot as stale, or removes only
          the opponent XI, never the league context.
        </p>
        <Link className="text-link" href="/matchday/">
          Open the matchday dashboard →
        </Link>
      </section>

      <section className="card" data-contract="methodology.transfers">
        <div className="section-head">
          <div>
            <p className="eyebrow">Transfers</p>
            <h2>Confirmed business only</h2>
          </div>
          <span className="badge badge-warn">Curated</span>
        </div>
        <p>
          The transfer register publishes completed permanent, loan and free moves
          only. API-Football is the candidate feed; official AFC announcements and
          Wikipedia season records are the cross-checks. Fees are not in the feed
          and are curated only: undisclosed is never zero and is excluded from net
          spend. Loan end, recall and obligation terms are unknown unless
          confirmed.
        </p>
        <Link className="text-link" href="/transfers/">
          Open the transfer register →
        </Link>
      </section>

      <section className="card" data-contract="methodology.history">
        <div className="section-head">
          <div>
            <p className="eyebrow">History</p>
            <h2>The Cormack era, measured and read</h2>
          </div>
          <span className="badge badge-neutral">One fact, one home</span>
        </div>
        <p>
          The history layer joins the measured league record, curated staff and
          honours, transfer windows, style proxies and lineup-based selection.
          Manager records are league-only; a match in a gap is unattributed.
          Style is opponent-unadjusted match-stat proxies, not xG. Selection is
          unavailable rather than inferred when the historical backfill is
          missing.
        </p>
        <p className="fine-print">
          &ldquo;The read&rdquo; is a labelled editorial assessment, not a
          measurement or the club&apos;s internal view. The 2023-24 League Cup
          was a runners-up finish and is not in the honours cabinet.
        </p>
        <Link className="text-link" href="/history/">
          Open the Cormack-era record →
        </Link>
      </section>

      <section className="card" data-contract="methodology.player-output">
        <div className="section-head">
          <div>
            <p className="eyebrow">Squad</p>
            <h2>Current-season player output</h2>
          </div>
          <span className="badge badge-neutral">Current season only</span>
        </div>
        <p>
          The squad is the current licensed squad plus current-season loanees out
          from the confirmed register. Each player has per-competition goals,
          assists, cards and the provider rating, plus shots/passes for outfield
          players and saves/conceded for goalkeepers. Starts, substitute
          appearances and on-pitch minutes are reconstructed from fixture lineups
          and substitution events, so a start and a substitute appearance are
          different numbers rather than one “apps” total.
        </p>
        <p>
          <strong>Role is a primary dimension, not a decorative attribute.</strong>{" "}
          The licensed team sheet gives the formation and each starter&apos;s grid
          slot. A starting right-back, centre-back, centre-midfielder, winger or
          forward is read from that grid; a substitute has no grid slot and
          therefore no role. A missing grid or an unmapped formation is shown as
          unknown, not filled with the generic squad position. Kick-off shape,
          centre-back count and holding-midfielder count are recorded for the
          shape/balance view. Mid-game formation switches are not in the feed and
          are never inferred from substitutions; reported ones are kept as
          sourced context notes.
        </p>
        <p>
          <strong>Positions are an eligibility set, not one label.</strong> The
          career layer uses FM-style slots (`D/WB L`, `DM/M C`, `AM R`, ...) from
          the last three seasons of starting-XI evidence, with primary,
          secondary and stretch tiers. Equal weight is given to starts; a
          one-off start is a stretch role, not a new primary. The broad filter is
          defenders/midfielders/attackers and left/centre/right. A full-back or
          wing-back counts as both a defender and a midfielder; a DM is a
          midfielder; a winger is an attacker. The current Aberdeen role is
          itself a multi-slot summary and only replaces the display label when
          it is clearly different. Curated role notes cover interpretations the
          kick-off grid cannot see, such as an inside forward or inverted
          full-back. This is a general football model for fluid formations and
          utility players, not an Aberdeen exception. See
          <code>docs/career-roles.md</code>.
        </p>
        <p>
          The player page is a projection of one typed document, with five
          panels: identity, position inference, playing time, performance and
          records. Each fact has one home; unknown attributes are omitted rather
          than repeated as caveats. See <code>docs/player-page-spec.md</code>.
        </p>
        <p>
          A measured zero stays zero; a missing row is <strong>unavailable</strong>{" "}
          and a row missing a key field is <strong>partial</strong>. Parent-club
          rows are never presented as loan-club output. Provider ratings are
          labelled as such and do not rank players. Goals conceded while on the
          pitch, clean sheets (60+ minutes, zero conceded on the pitch) and own
          goals are reconstructed from fixture lineups and events; a missing
          fixture is excluded and the coverage is labelled.
        </p>
        <p className="fine-print">
          Preferred foot is the one profile attribute the team sheet does not
          contain. It comes from a separate provenance pipeline: Sportmonks when
          its licensed adapter is enabled, then an official page only if it states
          the attribute, then Wikipedia as a last resort, then Unknown. Wikipedia
          values carry a page revision and permalink; no article text is
          published. The front end never infers a value. Side is derived from the
          role, not from preferred foot. Player photographs are not published.
          Current player names link to their profile wherever they appear in
          structured data; former players and rumour targets do not link. The
          2026-27 rebuild and shape-instability context is recorded in
          <code>docs/context/aberdeen-2026-27.md</code>.
        </p>
        <Link className="text-link" href="/squad/">
          Open the current squad →
        </Link>
      </section>

      <section className="card" data-contract="methodology.registers">
        <div className="section-head">
          <div>
            <p className="eyebrow">Rumours and fan signal</p>
            <h2>Two registers, one record</h2>
          </div>
          <span className="badge badge-warn">Separate from confirmed business</span>
        </div>
        <p>
          A rumour is an unconfirmed link with public sources, a lifecycle status
          and an editorial confidence. It becomes confirmed only when the move is in
          the transfer register, and then it links to that row. Status is not a
          probability.
        </p>
        <p>
          The fan signal samples the first page of recent AFC Chat Rumour Mill
          topics. Names are extracted with a player gazetteer and labelled by
          cross-reference: press rumour, club output, recent confirmed transfer or
          current squad. Sentiment is rule-based VADER on sampled posts, press
          claims and club titles. It is descriptive and noisy, not a poll.
        </p>
        <p className="fine-print">
          No raw post bodies, usernames or quotes are published. The forum
          advertises <code>ai-train=no, use=reference</code>; fitba does not train
          on the text. The active rumour cohort also produces an advisory
          recruitment profile, which never overrides the scouting fit. Community
          votes and submissions are a deferred separate project.
        </p>
        <Link className="text-link" href="/rumours/">
          Open the rumour mill →
        </Link>
      </section>

      <section className="card" data-contract="methodology.xg">
        <div className="section-head">
          <div>
            <p className="eyebrow">fxG</p>
            <h2>Model output, labelled</h2>
          </div>
          <span className="badge badge-neutral">experimental</span>
        </div>
        <p>
          fxG is fitba&apos;s own team-match expected-goals estimate. It uses
          open-play inside/outside-box shots, shots on target, blocked shots and
          a fixed penalty value, fitted to provider xG. It publishes an 80%
          model range for the estimate and a separate 80% goals range for the
          same chances. It has no shot coordinates, distance, angle, pressure,
          goalkeeper position or game state.
        </p>
        <p>
          Provider xG is carried separately where available and is never blended
          into fxG. The model is validated against 2026-27 provider xG; the gate
          is an in-season calibration, not an out-of-season holdout, and the
          values are descriptive rather than a performance verdict.
        </p>
        <p className="fine-print">
          <Link className="text-link" href="/analysis/xg/">
            fxG model card →
          </Link>{" "}
          <Link className="text-link" href="/matches/">
            Results and fixtures →
          </Link>
        </p>
      </section>

      <section className="card" data-contract="methodology.policy">
        <div className="section-head">
          <div>
            <p className="eyebrow">Policy</p>
            <h2>What is not published</h2>
          </div>
        </div>
        <ul className="plain-list">
          <li>No raw source payloads, full event feeds or source-shaped tables.</li>
          <li>No raw forum post bodies, usernames or quotes.</li>
          <li>No raw market-value feeds; only bands and our derived scores.</li>
          <li>No club crests or player photographs without a licence.</li>
          <li>No odds in the public app.</li>
          <li>No affiliation with Aberdeen FC, the SPFL or any provider.</li>
        </ul>
        <p className="fine-print">
          A source can be disabled in <code>config/sources.yaml</code> and the site rebuilt
          from the remaining sources. See <code>docs/sources.md</code> and{" "}
          <code>DATA_LICENSE.md</code>.
        </p>
        <p className="fine-print">
          Every published number has a registry entry, a declared formula, source
          layer and coverage tier, and an audit result on{" "}
          <Link href="/metrics/">Metrics and audit</Link>. A number whose mode is{" "}
          <code>provenance_only</code> is present and source-checked, not
          independently recomputed.
        </p>
        <Link className="text-link" href="/status/">
          Data status and freshness →
        </Link>
      </section>
    </ContractPage>
  );
}
