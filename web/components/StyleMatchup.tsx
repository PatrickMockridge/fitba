import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import type { StylePair, StyleProfile } from "@/lib/data";

const APPROACHES = [
  { key: "sit_deep_counter", label: "Sit deep" },
  { key: "balanced", label: "Balanced" },
  { key: "attack", label: "Attack" },
];

function value(value: number | null | undefined, suffix = "") {
  return value === null || value === undefined ? "—" : `${value}${suffix}`;
}

function ProfileMetrics({ profile }: { profile: StyleProfile }) {
  const rows = [
    ["Shots for", value(profile.shots_for_pm)],
    ["Shots against", value(profile.shots_against_pm)],
    ["Shot share", value(profile.shot_share !== null && profile.shot_share !== undefined ? Math.round(profile.shot_share * 100) : null, "%")],
    ["On target", value(profile.shots_on_target_for_pm)],
    ["Goals for", value(profile.goals_for_pm)],
    ["Goals against", value(profile.goals_against_pm)],
    ["Corners", value(profile.corners_for_pm)],
  ];
  return (
    <dl className="style-metrics">
      {rows.map(([label, metric]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{metric}</dd>
        </div>
      ))}
    </dl>
  );
}

function splitName(profile: StyleProfile) {
  return profile.venue === "H" ? "Home" : profile.venue === "A" ? "Away" : "All";
}

function StyleCard({
  name,
  pair,
  isAberdeen = false,
}: {
  name: string;
  pair: StylePair;
  isAberdeen?: boolean;
}) {
  const { lean, venue, overall } = pair;
  const index = lean.approach_index ?? 0;
  return (
    <article className={`style-card${isAberdeen ? " is-aberdeen" : ""}`}>
      <div className="style-card-head">
        <div>
          <p className="eyebrow">Measured shot profile</p>
          <h3>{name}</h3>
        </div>
        <ConfidenceBadge confidence={lean.confidence} />
      </div>
      <p className="style-lean-label">{lean.label}</p>
      <div className="lean-meter" aria-label={`Approach index ${index} of 100`}>
        <span className="lean-track">
          <span className="lean-fill" style={{ width: `${Math.max(0, Math.min(100, index))}%` }} />
        </span>
        <span className="lean-scale">
          <span>Deep</span>
          <span>Balanced</span>
          <span>Attack</span>
        </span>
      </div>
      <div className="lean-segments" aria-hidden="true">
        {APPROACHES.map((approach) => (
          <span
            key={approach.key}
            className={lean.approach === approach.key ? "is-active" : undefined}
          >
            {approach.label}
          </span>
        ))}
      </div>
      <ul className="style-evidence">
        {lean.evidence.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <p className="fine-print">
        {venue.matches} matches in this venue split
        {lean.venue_used ? " · venue-weighted read" : " · overall read carries more weight"}
      </p>
      <ProfileMetrics profile={venue} />
      <div className="table-wrap">
        <table className="league-table compact style-split-table">
<caption className="fine-print">Shot profile and approach index by venue split.</caption>
          <thead>
            <tr>
              <th>Split</th>
              <th className="num">Shots for</th>
              <th className="num">Shots against</th>
              <th className="num">Shot share</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Overall</td>
              <td className="num">{overall.shots_for_pm ?? "—"}</td>
              <td className="num">{overall.shots_against_pm ?? "—"}</td>
              <td className="num">
                {overall.shot_share === null || overall.shot_share === undefined
                  ? "—"
                  : `${Math.round(overall.shot_share * 100)}%`}
              </td>
            </tr>
            <tr>
              <td>{splitName(venue)}</td>
              <td className="num">{venue.shots_for_pm ?? "—"}</td>
              <td className="num">{venue.shots_against_pm ?? "—"}</td>
              <td className="num">
                {venue.shot_share === null || venue.shot_share === undefined
                  ? "—"
                  : `${Math.round(venue.shot_share * 100)}%`}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="fine-print">{pair.overall.note}</p>
      <p className="fine-print" data-contract-indicator="unknown">
        Possession: unknown
        {pair.overall.possession_unknown_reason
          ? ` (${pair.overall.possession_unknown_reason.replaceAll("_", " ")})`
          : ""}
        .
      </p>
    </article>
  );
}

export function StyleMatchup({
  aberdeenName,
  opponentName,
  aberdeen,
  opponent,
  venueLabel,
  aberdeenFirst,
  contract,
}: {
  aberdeenName: string;
  opponentName: string;
  aberdeen: StylePair;
  opponent: StylePair;
  venueLabel: string;
  aberdeenFirst: boolean;
  contract?: string;
}) {
  const first = aberdeenFirst
    ? { name: aberdeenName, pair: aberdeen, isAberdeen: true }
    : { name: opponentName, pair: opponent, isAberdeen: false };
  const second = aberdeenFirst
    ? { name: opponentName, pair: opponent, isAberdeen: false }
    : { name: aberdeenName, pair: aberdeen, isAberdeen: true };
  return (
    <section className="card style-matchup" data-contract={contract}>
      <div className="section-head">
        <div>
          <p className="eyebrow">Style and likely approach</p>
          <h2>How the styles meet</h2>
        </div>
        <span className="badge badge-neutral">{venueLabel} splits</span>
      </div>
      <div className="style-grid">
        <StyleCard
          name={first.name}
          pair={first.pair}
          isAberdeen={first.isAberdeen}
        />
        <StyleCard
          name={second.name}
          pair={second.pair}
          isAberdeen={second.isAberdeen}
        />
      </div>
      <p className="fine-print">
        The lean is inferred from measured shot volume, shot share, shots on
        target and goals. It is not xG and not a tactical model. Possession is
        not used.
      </p>
    </section>
  );
}
