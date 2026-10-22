import Link from "next/link";
import { AvailabilityBadge } from "@/components/AvailabilityBadge";
import type { NeedsDocument, NeedsFamily } from "@/lib/data";
import { formatDecimal, formatPercent } from "@/lib/format";

const CATEGORY_CLASS: Record<string, string> = {
  cover: "badge-warn",
  replace: "badge-warn",
  strengthen: "badge-neutral",
  monitor: "badge-neutral",
  none: "badge-ok",
  unknown: "badge-neutral",
};

function pct(value: unknown) {
  if (typeof value !== "number") return "—";
  return formatPercent(value);
}

function num(value: unknown) {
  if (typeof value !== "number") return "—";
  return formatDecimal(value).replace(/\.00$/, "");
}

function FamilyCard({ family }: { family: NeedsFamily }) {
  const measured = family.measured as Record<string, unknown>;
  const route = family.market_route ?? {};
  const roster = family.roster_space ?? {};
  const anchor = family.family.toLowerCase().replaceAll("/", "-");
  return (
    <article
      className="need-card"
      id={`needs-${anchor}`}
      data-contract="recruitment.needs-family"
    >
      <div className="need-head">
        <div>
          <p className="eyebrow" data-contract="recruitment.needs-priority">
            Priority {family.priority ?? "—"} · {family.urgency}
          </p>
          <h3>{family.label}</h3>
        </div>
        <div className="badge-row" data-contract="recruitment.needs-confidence">
          <span className={`badge ${CATEGORY_CLASS[family.category] ?? "badge-neutral"}`}>
            {family.category.replaceAll("_", " ")}
          </span>
          <span
            className="badge badge-neutral"
            data-contract-indicator="confidence"
          >
            {family.confidence} confidence
          </span>
        </div>
      </div>

      <div className="need-metrics">
        <span>
          <span className="stat-label">Expected slots</span>
          <strong>{num(family.expected_slots)}</strong>
        </span>
        <span>
          <span className="stat-label">Available</span>
          <strong>{String(measured.available_players ?? "—")}</strong>
        </span>
        <span>
          <span className="stat-label">Ready</span>
          <strong>{String(measured.ready_count ?? "—")}</strong>
        </span>
        <span>
          <span className="stat-label">Starts 3+</span>
          <strong>{String(measured.trusted_count ?? "—")}</strong>
        </span>
        <span>
          <span className="stat-label">Top share</span>
          <strong>{pct(measured.top_share)}</strong>
        </span>
        <span>
          <span className="stat-label">Availability risk</span>
          <strong>{pct(measured.availability_risk)}</strong>
        </span>
      </div>
      {measured.availability_risk == null ? (
        <p className="fine-print">
          Availability risk is unknown: {String(measured.availability_known ?? 0)} known /{" "}
          {String(measured.availability_unknown ?? "—")} unknown projected players.
        </p>
      ) : null}

      <p className="need-line">
        {family.category === "cover"
          ? "Short-term cover is the proportionate response; the market route is loan or free agent."
          : family.category === "strengthen"
            ? "The measured depth or quality points to a structural strengthening need, not just a short-term body."
            : family.category === "replace"
              ? "An active public outgoing link makes a replacement scenario worth monitoring; no bid or contract claim is made."
              : family.category === "unknown"
                ? "There is not enough measured depth to classify this family."
                : "No measured need at this publish."}
      </p>

      <div className="need-grid">
        <div className="mini-block">
          <p className="eyebrow">Drivers</p>
          <p>{family.drivers.length ? family.drivers.join(" · ") : "—"}</p>
        </div>
        <div className="mini-block" data-contract="recruitment.needs-market-route">
          <p className="eyebrow">Market route</p>
          <p>
            {route.primary ?? "none"}
            {route.alternatives?.length
              ? ` · alternatives: ${route.alternatives.join(", ")}`
              : ""}
          </p>
          <p className="fine-print">
            Fee: {route.fee_expectation ?? "unknown"} · budget:{" "}
            {(route.budget_status ?? "unknown").replaceAll("_", " ")} · wages:{" "}
            {(route.wage_status ?? "unknown").replaceAll("_", " ")}
          </p>
        </div>
        <div className="mini-block" data-contract="recruitment.needs-roster">
          <p className="eyebrow">Roster</p>
          <p>
            {String(roster.current ?? "—")} / {String(roster.max_squad ?? "—")} in
            the family
          </p>
          <p className="fine-print">
            {roster.note ?? "No public senior-squad limit is known."}
          </p>
        </div>
        <div className="mini-block">
          <p className="eyebrow">Analyst intent</p>
          <p>
            Curated prior:{" "}
            <strong>
              {family.curated_prior === null || family.curated_prior === undefined
                ? "—"
                : `${Math.round(family.curated_prior * 100)}%`}
            </strong>
          </p>
          <p className="fine-print">
            Shown separately from the measured evidence; it is not a verdict.
          </p>
        </div>
      </div>

      <details
        className="need-details"
        data-contract="recruitment.needs-players"
        open
      >
        <summary>
          Players and availability ({family.players.length})
        </summary>
        <div className="table-wrap">
          <table className="league-table compact">
<caption className="fine-print">Squad needs by family with availability and market route.</caption>
            <thead>
              <tr>
                <th>Player</th>
                <th>Category</th>
                <th className="num">Starts</th>
                <th className="num">Minutes</th>
                <th className="num">Sub apps</th>
                <th>Availability</th>
              </tr>
            </thead>
            <tbody>
              {family.players.map((player) => (
                <tr key={`${family.family}-${player.player_id}`}>
                  <td className="strong">{player.name ?? "Unknown"}</td>
                  <td>{player.category ?? "—"}</td>
                  <td className="num">{player.starts ?? 0}</td>
                  <td className="num">{player.minutes ?? 0}</td>
                  <td className="num">{player.sub_apps ?? 0}</td>
                  <td>
                    <AvailabilityBadge
                      status={player.availability_status}
                      note={player.availability_note}
                      compact
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <div className="theme-links">
        {["cover", "replace", "strengthen"].includes(family.category) ? (
          <Link className="text-link" href={`/scouting/#priority-${anchor}`}>
            Scouting profile →
          </Link>
        ) : null}
        <Link className="text-link" href="/squad/">
          Squad →
        </Link>
        <Link className="text-link" href="/analysis/">
          Data analysis →
        </Link>
      </div>
    </article>
  );
}

export function NeedsBoard({ data }: { data: NeedsDocument }) {
  const counts = data.summary.counts ?? {};
  return (
    <section
      className="section"
      id="squad-needs"
      data-contract="recruitment.needs-board"
    >
      <div className="section-head">
        <div>
          <p className="eyebrow">Data analysis → recruitment</p>
          <h2>Squad needs</h2>
        </div>
        <span className="badge badge-neutral">
          {data.summary.families ?? 0} role families
        </span>
      </div>
      <div className="stat-row four" data-contract="recruitment.needs-summary">
        <div className="stat-tile">
          <span className="stat-label">Cover</span>
          <span className="stat-value">{counts.cover ?? 0}</span>
          <span className="stat-note">short-term loan/free</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Strengthen</span>
          <span className="stat-value">{counts.strengthen ?? 0}</span>
          <span className="stat-note">structural</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Replace</span>
          <span className="stat-value">{counts.replace ?? 0}</span>
          <span className="stat-note">evidence-only</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Availability known</span>
          <span className="stat-value">
            {data.summary.availability_known ?? 0}/
            {(data.summary.availability_known ?? 0) +
              (data.summary.availability_unknown ?? 0)}
          </span>
          <span className="stat-note" data-contract-indicator="unknown">
            unknown stays unknown
          </span>
        </div>
      </div>
      <p className="fine-print">
        Role profiles and market routes only. No specific targets, fees or wages.
        The measured depth/availability drives the category; the curated prior is
        shown separately. Availability is a special case of team news. With{" "}
        {data.summary.availability_known ?? 0} known and{" "}
        {data.summary.availability_unknown ?? 0} unknown entries, injury cover
        cannot be classified for players without a verified public team-news
        record; context-only names are not published and do not change the model.
      </p>
      <div className="needs-grid">
        {data.families.map((family) => (
          <FamilyCard family={family} key={family.family} />
        ))}
      </div>
    </section>
  );
}
