import Link from "next/link";
import { AvailabilityBadge } from "@/components/AvailabilityBadge";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { formatPercent } from "@/lib/format";
import { PitchLineup } from "@/components/PitchLineup";
import { PlayerLink } from "@/components/PlayerLink";
import type { LineupBlock } from "@/lib/data";

function coverageLabel(block: LineupBlock) {
  const coverage = block.coverage ?? {};
  if (!coverage.fixtures_with_lineups) return "No lineup sample";
  const total = coverage.fixtures_total ?? coverage.fixtures_with_lineups;
  const share =
    coverage.lineup_coverage !== null && coverage.lineup_coverage !== undefined
      ? ` (${Math.round(coverage.lineup_coverage * 100)}%)`
      : "";
  return `${coverage.fixtures_with_lineups}/${total} matches with lineups${share}`;
}

export function PredictedLineupPanel({
  teamName,
  block,
  isAberdeen = false,
  contract,
}: {
  teamName: string;
  block: LineupBlock | null;
  isAberdeen?: boolean;
  contract?: string;
}) {
  if (!block || block.status === "unavailable") {
    return (
      <article
        className={`card lineup-panel${isAberdeen ? " is-aberdeen" : ""}`}
        data-contract={contract}
      >
        <div className="card-head">
          <div>
            <p className="eyebrow">Predicted XI</p>
            <h2>{teamName}</h2>
          </div>
          <span className="badge badge-neutral">Unavailable</span>
        </div>
        <p className="muted" data-contract-indicator="unknown">
          {block?.reason
            ? `No prediction: ${block.reason.replaceAll("_", " ")}.`
            : "No prediction is made without an observed lineup window."}
        </p>
        {block?.note ? <p className="fine-print">{block.note}</p> : null}
        <p className="fine-print">
          <strong>Predicted, not team news.</strong> No lineup is fabricated when
          the sample is missing.
        </p>
      </article>
    );
  }

  return (
    <article
      className={`card lineup-panel${isAberdeen ? " is-aberdeen" : ""}`}
      data-contract={contract}
    >
      <div className="card-head">
        <div>
          <p className="eyebrow">Predicted XI · not team news</p>
          <h2>{teamName}</h2>
        </div>
        <div className="badge-row" data-contract="matchday.lineup.formation-confidence">
          <span className="badge badge-neutral">{block.formation ?? "—"}</span>
          {block.formation_confidence ? (
            <ConfidenceBadge confidence={block.formation_confidence} compact />
          ) : null}
        </div>
      </div>

      <div className="mini-block">
        <span className="stat-label">Selection confidence</span>{" "}
        <ConfidenceBadge confidence={block.team_confidence ?? "unknown"} />
        <span className="fine-print">
          {" "}
          · {coverageLabel(block)}
          {block.slot_count
            ? ` · ${block.filled}/${block.slot_count} slots filled`
            : ""}
        </span>
        {block.availability?.applicable &&
        (block.availability.known ?? 0) + (block.availability.unknown ?? 0) > 0 ? (
          <span className="fine-print">
            {" "}
            · team news {block.availability.known ?? 0} known,{" "}
            {block.availability.unknown ?? 0} unknown
          </span>
        ) : null}
        <p className="fine-print">
          Confidence measures the selection evidence only: starts, minutes, role
          fit, form and the observed formation.{" "}
          {block.availability?.applicable
            ? "Unknown team news is shown as a separate availability state and does not lower this estimate."
            : "Opponent availability is not modelled."}
        </p>
      </div>

      {block.selection ? (
        <div className="mini-block" data-contract="matchday.lineup.selection-weights">
          <span className="stat-label">Selection inputs</span>
          <span className="fine-print">
            {" "}
            form {formatPercent(block.selection.weights?.form ?? 0)} · minute share{" "}
            {formatPercent(block.selection.weights?.minute_share ?? 0)} · recent
            rating {formatPercent(block.selection.weights?.recent_rating ?? 0)} · role
            fit {formatPercent(block.selection.weights?.role_fit ?? 0)} · start rate{" "}
            {formatPercent(block.selection.weights?.start_rate ?? 0)} · recency{" "}
            {formatPercent(block.selection.weights?.recency_start ?? 0)}
          </span>
          {block.selection.rating_coverage ? (
            <span className="fine-print">
              {" "}
              · rating coverage:{" "}
              {block.selection.rating_coverage.available ?? 0} available,{" "}
              {block.selection.rating_coverage.partial ?? 0} partial,{" "}
              {block.selection.rating_coverage.unavailable ?? 0} unavailable
            </span>
          ) : null}
        </div>
      ) : null}

      {block.availability ? (
        <div className="mini-block" data-contract="matchday.lineup.availability">
          <span className="stat-label">Availability</span>{" "}
          <AvailabilityBadge
            status={block.availability.state}
            note={block.availability.note}
            compact
          />
          <span className="fine-print">
            {" "}
            {block.availability.applicable === false ||
            block.availability.known == null ||
            block.availability.unknown == null
              ? "Not modelled for opponents"
              : `${block.availability.known} known · ${block.availability.unknown} unknown`}
            {block.availability.as_of ? ` · as of ${block.availability.as_of}` : ""}
          </span>
        </div>
      ) : null}

      <PitchLineup
        players={block.players}
        formation={block.formation}
        teamName={teamName}
        contract="matchday.lineup.pitch"
      />

      <section className="contenders" data-contract="matchday.lineup.contenders">
        <div className="section-head">
          <h3>Contenders</h3>
          <span className="badge badge-neutral">
            {block.contenders.length} next in line
          </span>
        </div>
        <ul className="contender-list">
          {block.contenders.map((player) => (
            <li key={`${player.player_id}-${player.slot ?? "bench"}`}>
              <span className="contender-slot">
                {player.role_code ?? player.slot ?? "—"}
              </span>
              <PlayerLink
                name={player.name ?? `Player ${player.player_id}`}
                href={player.href}
              />
              <span className="muted">
                {player.starts ?? 0} starts · {player.minutes ?? 0} mins · form{" "}
                {Math.round((player.form ?? 0) * 100)} · rating{" "}
                {player.recent_rating ?? "—"}
              </span>
              <AvailabilityBadge
                status={player.availability_status}
                note={player.availability_note}
                compact
              />
              <ConfidenceBadge confidence={player.confidence} compact />
            </li>
          ))}
        </ul>
      </section>

      <details
        className="lineup-details"
        data-contract="matchday.not-considered"
        open
      >
        <summary>Not considered ({block.unavailable.length})</summary>
        {block.unavailable.length ? (
          <ul className="plain-list">
            {block.unavailable.map((player) => (
              <li key={`${player.player_id}-${player.reason}`}>
                <span>{player.name}</span>{" "}
                <span className="muted">
                  {player.reason.replaceAll("_", " ")}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">None recorded in this snapshot.</p>
        )}
      </details>

      <p className="fine-print">{block.disclaimer}</p>
      {block.note ? <p className="fine-print">{block.note}</p> : null}
      <p className="fine-print">
        {isAberdeen ? (
          <Link className="text-link" href="/squad/">
            Current squad →
          </Link>
        ) : (
          "Opponent players are not linked to fitba profiles."
        )}
      </p>
    </article>
  );
}
