import Link from "next/link";
import { PlayerRose } from "@/components/PlayerRose";
import { ProfileHeader } from "@/components/ProfileHeader";
import { ProfileSection } from "@/components/ProfileSection";
import type {
  ScoutingArchetypeDefinition,
  ScoutingPlayer,
  ScoutingPriorityConfig,
  ScoutingSearchRow,
} from "@/lib/data";
import { formatDate, formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";
import type { RoseCatalogue } from "@/lib/rose";



const EUROPE_LABELS: Record<string, string> = {
  "UEFA Champions League": "Champions League",
  "UEFA Europa League": "Europa League",
  "UEFA Conference League": "Conference League",
};

const STATUS_LABELS: Record<string, string> = {
  qualified: "90+ league-phase minutes — discounted",
  below_threshold: "Below 90 league-phase minutes — not discounted",
  none: "No league-phase minutes in the covered competitions",
  unknown: "European status unknown — not discounted",
};

function value(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? "—" : formatDecimal(value, digits);
}

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : formatPercentValue(value, 1);
}

export function ScoutingProfile({
  player,
  priority,
  archetypes,
  others,
  leagueSlug,
  leagueName,
  roseCatalogue,
}: {
  player: ScoutingPlayer;
  priority: ScoutingPriorityConfig;
  archetypes: ScoutingArchetypeDefinition[];
  others: ScoutingSearchRow[];
  leagueSlug: string;
  leagueName: string;
  roseCatalogue: RoseCatalogue;
}) {
  const labels = new Map(archetypes.map((item) => [item.id, item.label]));
  const profileEntries = Object.entries(player.archetypes ?? {});
  const u23 = player.age !== null && player.age <= priority.u23_max_age;
  const displayName = player.full_name || player.name;
  const former = player.former_aberdeen ?? null;

  return (
    <section className="section">
      <ProfileHeader
        eyebrow={`Scouting profile · ${player.club} · ${player.role_label}`}
        name={displayName}
        lede={
          former ? (
            <>
              A standard scouting profile for {player.name}, shown with the additional
              former-Aberdeen record. Current or last known club: {player.club}. Statistical
              basis:{" "}
              {former.stats_basis === "post_career_league"
                ? `the latest post-Aberdeen league season at ${player.stats_club}`
                : former.stats_basis === "aberdeen_last_season"
                  ? "the last covered Aberdeen season"
                  : former.stats_basis === "scouting_current_season"
                    ? `the current scouting season at ${player.stats_club}`
                    : "no measured league season"}. It is not a target, a recommendation, a
              fee or a contract claim.
            </>
          ) : (
            <>
              A licensed-feed scouting profile for {player.name}. Current club: {player.club}. The
              statistics were produced at {player.stats_club} in the {leagueName}. It is not a
              target, a recommendation, a fee or a contract claim.
            </>
          )
        }
        badges={
          <>
            <span className="badge badge-neutral">
              {player.nationality ?? "Nationality unknown"}
            </span>
            <span className="badge badge-neutral">Age {value(player.age, 0)}</span>
            {u23 ? <span className="badge badge-neutral">U23</span> : null}
            {former ? <span className="badge badge-warn">Former Aberdeen player</span> : null}
            <span className="badge badge-neutral">{player.role_label}</span>
            {player.stats_club && player.stats_club !== player.club ? (
              <span className="badge badge-warn">
                moved {player.transferred_at ? `· ${player.transferred_at}` : ""}
              </span>
            ) : null}
            {player.european_status === "qualified" ? (
              <span className="badge badge-warn">European shop window</span>
            ) : null}
          </>
        }
      />

      {player.rose ? (
        <PlayerRose
          rose={player.rose}
          playerName={displayName}
          idPrefix={`scouting-${player.player_id}`}
          catalogue={roseCatalogue}
        />
      ) : (
        <div className="data-panel" data-contract="player-profile.rose">
          <p>The statistical profile is unavailable in this build.</p>
        </div>
      )}

      <ProfileSection
        id="key-facts"
        eyebrow="Key facts"
        title="Season summary"
        badge={leagueName}
        indicator="basis"
        contract="player-profile.summary"
      >
        <div className="stat-row four">
          <div className="stat-tile">
            <span className="stat-label">Minutes</span>
            <span className="stat-value">{formatInteger(player.minutes)}</span>
            <span className="stat-note">{formatInteger(player.appearances ?? 0)} appearances</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Provider rating</span>
            <span className="stat-value">{value(player.rating)}</span>
            <span className="stat-note">opaque; not a verdict</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Percentile</span>
            <span className="stat-value">{pct(player.rating_percentile)}</span>
            <span className="stat-note">within league and role</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Adjusted percentile</span>
            <span className="stat-value">{pct(player.adjusted_percentile)}</span>
            <span className="stat-note">empirical Premiership alignment</span>
          </div>
        </div>
      </ProfileSection>

      {player.former_aberdeen ? (
        <ProfileSection
          id="former-aberdeen"
          eyebrow="Former Aberdeen player"
          title="Aberdeen and after"
          badge="Former-player register"
          indicator="unknown"
          contract="player-profile.former"
          note={
            player.former_aberdeen.stats_basis === "aberdeen_last_season"
              ? "No measured post-Aberdeen league season is available at the profile threshold; the statistical profile above uses the last covered Aberdeen season."
              : player.former_aberdeen.stats_basis === "post_career_league"
                ? "The statistical profile above uses the latest measured post-Aberdeen league season."
                : player.former_aberdeen.stats_basis === "scouting_current_season"
                  ? "The statistical profile above is the current scouting season. The former-Aberdeen record is additional context, not a second statistical profile."
                  : "No measured league season is available; only the former-player record is published."
          }
        >
          <p>
            Left Aberdeen on{" "}
            {player.former_aberdeen.departure.date
              ? formatDate(player.former_aberdeen.departure.date)
              : "an unknown date"}{" "}
            for {player.former_aberdeen.departure.to_club_name ?? "an unknown club"} ·{" "}
            {player.former_aberdeen.departure.kind ?? "move"} ·{" "}
            {player.former_aberdeen.departure.fee_display ?? "fee unknown"}.
          </p>
          <div className="stat-row four">
            <div className="stat-tile">
              <span className="stat-label">Aberdeen apps</span>
              <span className="stat-value">
                {player.former_aberdeen.aberdeen.appearances === null
                  ? "—"
                  : formatInteger(player.former_aberdeen.aberdeen.appearances)}
              </span>
              <span className="stat-note">
                {player.former_aberdeen.aberdeen.first_season ?? "—"} to{" "}
                {player.former_aberdeen.aberdeen.last_season ?? "—"}
              </span>
            </div>
            <div className="stat-tile">
              <span className="stat-label">Aberdeen minutes</span>
              <span className="stat-value">
                {player.former_aberdeen.aberdeen.minutes === null
                  ? "—"
                  : formatInteger(player.former_aberdeen.aberdeen.minutes)}
              </span>
              <span className="stat-note">covered competitive record</span>
            </div>
            <div className="stat-tile">
              <span className="stat-label">Post-Aberdeen league mins</span>
              <span className="stat-value">
                {player.former_aberdeen.post_career.totals.minutes === null ||
                player.former_aberdeen.post_career.totals.minutes === undefined
                  ? "—"
                  : formatInteger(player.former_aberdeen.post_career.totals.minutes)}
              </span>
              <span className="stat-note">
                {player.former_aberdeen.post_career.totals.seasons_with_data ?? 0} of{" "}
                {player.former_aberdeen.post_career.totals.seasons_expected ?? 0} seasons
              </span>
            </div>
            <div className="stat-tile">
              <span className="stat-label">Current or last known</span>
              <span className="stat-value">
                {player.former_aberdeen.post_career.current.club_name ?? "Unknown"}
              </span>
              <span className="stat-note">
                {player.former_aberdeen.post_career.current.coverage === "current"
                  ? "current-season provider row"
                  : "last known"}
              </span>
            </div>
          </div>
          <p className="fine-print">
            {player.former_aberdeen.aberdeen.developed_here === "yes"
              ? "Early-career Aberdeen proxy: yes. "
              : player.former_aberdeen.aberdeen.developed_here === "unknown"
                ? "Early-career Aberdeen proxy: unknown. "
                : "Early-career Aberdeen proxy: no. "}
            {player.former_aberdeen.post_career.at_rival
              ? `Rival spell: ${player.former_aberdeen.post_career.rival_spells
                  .map((spell) => `${spell.club} (${spell.from_season} to ${spell.to_season})`)
                  .join(", ")}. `
              : "No post-Aberdeen rival spell. "}
            {player.former_aberdeen.sell_on
              ? `Sell-on: ${
                  player.former_aberdeen.sell_on.sell_on_pct === null
                    ? "percentage undisclosed"
                    : `${player.former_aberdeen.sell_on.sell_on_pct}%`
                }, receipt ${player.former_aberdeen.sell_on.receipt.status.replaceAll("_", " ")}${
                  player.former_aberdeen.sell_on.receipt.missing_inputs.length
                    ? ` (missing: ${player.former_aberdeen.sell_on.receipt.missing_inputs.join(", ")})`
                    : ""
                }.`
              : "No sell-on clause recorded."}
          </p>
          <p className="fine-print">
            <Link href={player.former_aberdeen.href}>
              Former-player register entry
            </Link>
            {" · "}
            <Link href="/former-players/">All former players</Link>
            {" · "}
            <Link href="/methodology/">Method</Link>
          </p>
        </ProfileSection>
      ) : null}

      <ProfileSection
        eyebrow="Team context"
        title="Outperforming a struggling team"
        badge={player.team_underperforming ? "Bottom 40% by PPG" : "Context"}
        contract="player-profile.context"
      >
        {player.team_context_status === "available" ? (
          <>
            <div className="stat-row four">
              <div className="stat-tile">
                <span className="stat-label">League position</span>
                <span className="stat-value">
                  {player.team_rank ?? "—"}
                  <span className="muted">/{player.team_count ?? "—"}</span>
                </span>
                <span className="stat-note">points per game table</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">Team points</span>
                <span className="stat-value">{player.team_points ?? "—"}</span>
                <span className="stat-note">{player.team_played ?? "—"} played</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">Team PPG percentile</span>
                <span className="stat-value">{pct(player.team_points_percentile)}</span>
                <span className="stat-note">within the league</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">Team lift</span>
                <span className="stat-value">{value(player.team_lift, 1)}</span>
                <span className="stat-note">role-adjusted percentile minus team PPG percentile</span>
              </div>
            </div>
            <p className="fine-print">
              Team context is a contrast, not a valuation, forecast or recommendation. A
              team is treated as underperforming at or below the configured PPG percentile;
              a league without a table is unknown, not zero-strength.
            </p>
          </>
        ) : (
          <p className="fine-print">No current league table is available for this team.</p>
        )}
      </ProfileSection>

      <ProfileSection
        eyebrow="Profiles"
        title="Raw and adjusted archetype scores"
        badge={`${profileEntries.length} applicable`}
        contract="player-profile.output"
      >
        {profileEntries.length ? (
          <div className="table-wrap">
            <table className="league-table compact">
              <caption className="fine-print">
                Raw scores are within the player&apos;s league and role cohort; adjusted scores
                are mapped into the Premiership distribution. Coverage is the absolute feature
                weight present.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Profile</th>
                  <th className="num" scope="col">Raw</th>
                  <th className="num" scope="col">Adjusted</th>
                  <th className="num" scope="col">Coverage</th>
                </tr>
              </thead>
              <tbody>
                {profileEntries.map(([id, data]) => (
                  <tr key={id}>
                    <td>{labels.get(id) ?? id}</td>
                    <td className="num">{value(data.score, 1)}</td>
                    <td className="num">{value(data.adjusted_score, 1)}</td>
                    <td className="num">{pct((data.coverage ?? 0) * 100)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">No applicable profile at the coverage floor.</p>
        )}
      </ProfileSection>

      <div className="grid two-col">
        <ProfileSection
          eyebrow="Scouting context"
          title="Scouting priority"
          badge={
            player.cohort_basis === "former_player_only"
              ? "Not ranked"
              : formatDecimal(player.scouting_priority ?? 0, 1)
          }
          indicator="basis"
          contract="player-profile.context"
        >
          {player.cohort_basis === "former_player_only" ? (
            <p>
              This former-player profile is not in the current scouting pool, so no value index,
              scouting priority or Europe discount is inferred. The standard profile is shown for
              the record.
            </p>
          ) : (
            <>
              <p>
                Value index {formatDecimal(player.value_index ?? 0, 1)} × age multiplier{" "}
                {formatDecimal(player.age_multiplier ?? 1, 2)} × Europe multiplier{" "}
                {formatDecimal(player.europe_multiplier ?? 1, 2)} ={" "}
                {formatDecimal(player.scouting_priority ?? 0, 1)}.
              </p>
              <p className="fine-print">
                U23 ≤{formatInteger(priority.u23_max_age)} ×
                {formatDecimal(priority.u23_multiplier, 2)}; European league phase ≥
                {formatInteger(priority.europe_minutes_threshold)} min ×
                {formatDecimal(priority.europe_multiplier, 2)}. These are Aberdeen scouting
                preferences, not measured quality. The value index is not a transfer value.
              </p>
            </>
          )}
        </ProfileSection>

        <ProfileSection
          eyebrow="Scouting context"
          title="League-phase shop window"
          badge={player.cohort_basis === "former_player_only" ? "unknown" : player.european_status}
          contract="player-profile.context"
        >
          <p>
            {player.cohort_basis === "former_player_only"
              ? "No league-phase coverage is inferred for this former-player profile."
              : STATUS_LABELS[player.european_status] ?? player.european_status}
          </p>
          {player.cohort_basis === "former_player_only" ? null : (
            <p className="fine-print">
              {player.european_league_phase_minutes ?? 0} league-phase minutes across{" "}
              {player.european_league_phase_appearances ?? 0} appearances.
              {player.european_league_phase_competitions.length
                ? ` Competitions: ${player.european_league_phase_competitions
                    .map((name) => EUROPE_LABELS[name] ?? name)
                    .join(", ")}.`
                : ""}
            </p>
          )}
          <p className="fine-print">
            Only the league phase of the Champions League, Europa League and Conference League is
            covered; qualifiers and play-offs are excluded. Unknown is not “not in Europe” and is
            never discounted.
          </p>
        </ProfileSection>
      </div>

      <ProfileSection
        eyebrow="Coverage and limits"
        title="What this profile can and cannot say"
        badge="Source · API-Football"
        contract="player-profile.coverage"
      >
        <p>
          Current club: {player.club}
          {player.current_league_name ? ` (${player.current_league_name})` : ""}; 2026-27
          statistics at {player.stats_club} in the {leagueName}; {player.role_label}; role family{" "}
          {player.role_family ?? "unknown"}; cohort basis {player.cohort_basis}; cohort n{" "}
          {player.cohort_n ? formatInteger(player.cohort_n) : "—"}.
        </p>
        <p className="fine-print">
          The provider rating is opaque and relative to the player&apos;s league and role cohort.
          The adjusted percentile is an empirical Premiership alignment, not a measured
          equivalence. No contracts, wages, fees, release clauses or recommendations are claimed.
          Forward and progressive passes, carries, pressures and aerial wins are not in the feed.
        </p>
        {others.length ? (
          <p className="fine-print">
            Also in this build:{" "}
            {others
              .map((row) => `${row.l} (${formatInteger(row.m)} mins)`)
              .join(", ")}. The profile uses the most-minutes row.
          </p>
        ) : null}
        <p className="back-link">
          {leagueSlug === "former" ? (
            <Link href="/former-players/">← Former-player register</Link>
          ) : (
            <Link href={`/scouting/${leagueSlug}/`}>← League search</Link>
          )}
          {" · "}
          <Link href="/scouting/search/">Full search →</Link>
          {" · "}
          <Link href="/scouting/">Scouting board →</Link>
          {" · "}
          <Link href="/methodology/">Method →</Link>
          {" · "}
          <Link href="/sources/">Sources →</Link>
        </p>
      </ProfileSection>
    </section>
  );
}
