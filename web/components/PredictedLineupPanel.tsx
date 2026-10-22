import Link from "next/link";
import { PitchLineup } from "@/components/PitchLineup";
import { PlayerLink } from "@/components/PlayerLink";
import type { LineupBlock } from "@/lib/data";

function coverageLabel(block: LineupBlock) {
  const coverage = block.coverage ?? {};
  if (!coverage.fixtures_with_lineups) return "No lineup sample";
  const total = coverage.fixtures_total ?? coverage.fixtures_with_lineups;
  return `${coverage.fixtures_with_lineups}/${total} matches with lineups`;
}

export function PredictedLineupPanel({
  teamName,
  block,
  isAberdeen = false,
}: {
  teamName: string;
  block: LineupBlock | null;
  isAberdeen?: boolean;
}) {
  if (!block || block.status === "unavailable") {
    return (
      <article className="card lineup-panel">
        <div className="card-head">
          <div>
            <p className="eyebrow">Predicted XI · not team news</p>
            <h2>{teamName}</h2>
          </div>
        </div>
        <p className="muted">
          {block?.reason
            ? `No prediction: ${block.reason.replaceAll("_", " ")}.`
            : "No prediction is made without an observed lineup window."}
        </p>
      </article>
    );
  }

  const selection = block.selection;
  const availability = block.availability;

  return (
    <article className="card lineup-panel">
      <div className="card-head">
        <div>
          <p className="eyebrow">Predicted XI · not team news</p>
          <h2>{teamName}</h2>
        </div>
      </div>

      <p className="muted">
        {block.formation ?? "—"} · {block.team_confidence ?? "unknown"} confidence ·{" "}
        {coverageLabel(block)}
      </p>

      <PitchLineup
        players={block.players}
        formation={block.formation}
        teamName={teamName}
        listHidden
      />

      <details className="lineup-details">
        <summary>XI detail</summary>
        {selection ? (
          <p className="muted">
            Selection: form {Math.round((selection.weights?.form ?? 0) * 100)}% ·
            rating {Math.round((selection.weights?.recent_rating ?? 0) * 100)}% ·
            starts/recency{" "}
            {Math.round(
              ((selection.weights?.start_rate ?? 0) +
                (selection.weights?.recency_start ?? 0)) *
                100,
            )}
            % · rating coverage {selection.rating_coverage?.available ?? 0} available,{" "}
            {selection.rating_coverage?.partial ?? 0} partial,{" "}
            {selection.rating_coverage?.unavailable ?? 0} unavailable.
          </p>
        ) : null}

        {availability ? (
          <p className="muted">
            Availability: {availability.state ?? "unknown"} ·{" "}
            {availability.known ?? 0} known · {availability.unknown ?? 0} unknown
            {availability.as_of ? ` · as of ${availability.as_of}` : ""}.
          </p>
        ) : null}

        {block.contenders.length ? (
          <>
            <h3>Contenders</h3>
            <ul className="plain-list">
              {block.contenders.map((player) => (
                <li key={`${player.player_id}-${player.slot ?? "bench"}`}>
                  <span className="muted">{player.role_code ?? player.slot ?? "—"}</span>{" "}
                  <PlayerLink
                    name={player.name ?? `Player ${player.player_id}`}
                    href={player.href}
                  />{" "}
                  <span className="muted">
                    {player.starts ?? 0} starts · rating {player.recent_rating ?? "—"}
                  </span>
                </li>
              ))}
            </ul>
          </>
        ) : null}

        {block.unavailable.length ? (
          <p className="muted">
            Not considered: {block.unavailable.map((player) => player.name).join(", ")}.
          </p>
        ) : null}

        <p className="muted">{block.disclaimer}</p>
        {isAberdeen ? (
          <p>
            <Link className="text-link" href="/squad/">
              Current squad →
            </Link>
          </p>
        ) : null}
      </details>
    </article>
  );
}
