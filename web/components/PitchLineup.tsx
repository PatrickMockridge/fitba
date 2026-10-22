import { PlayerLink } from "@/components/PlayerLink";
import type { LineupPlayer } from "@/lib/data";

function rowOf(player: LineupPlayer) {
  const grid = player.grid ?? player.slot ?? "";
  const row = Number.parseInt(grid.split(":")[0] ?? "", 10);
  return Number.isFinite(row) ? row : 99;
}

function columnOf(player: LineupPlayer) {
  const grid = player.grid ?? player.slot ?? "";
  const column = Number.parseInt(grid.split(":")[1] ?? "", 10);
  return Number.isFinite(column) ? column : 99;
}

export function PitchLineup({
  players,
  formation,
  teamName,
  listHidden = false,
}: {
  players: LineupPlayer[];
  formation?: string | null;
  teamName: string;
  listHidden?: boolean;
}) {
  const rows = new Map<number, LineupPlayer[]>();
  for (const player of players) {
    const row = rowOf(player);
    const current = rows.get(row) ?? [];
    current.push(player);
    rows.set(row, current);
  }
  const ordered = [...rows.entries()].sort(([a], [b]) => a - b);

  return (
    <div className="pitch-wrap">
      <div className="pitch" aria-hidden="true">
        <div className="pitch-line pitch-line-mid" />
        <div className="pitch-circle" />
        {ordered.map(([row, rowPlayers]) => (
          <div className="pitch-row" key={row}>
            {rowPlayers
              .sort((a, b) => columnOf(a) - columnOf(b))
              .map((player, index) => (
                <div
                  className={`pitch-player confidence-${player.confidence || "unknown"}`}
                  key={`${row}-${player.player_id ?? index}`}
                >
                  <span className="pitch-number">
                    {player.shirt_number ?? "—"}
                  </span>
                  <span className="pitch-name">
                    {player.name ?? "Unknown player"}
                  </span>
                  <span className="pitch-role">
                    {player.role_code ?? player.role_label ?? "—"}
                  </span>
                  <span className="pitch-confidence">
                    {player.confidence || "unknown"}
                  </span>
                </div>
              ))}
          </div>
        ))}
      </div>
      <p className="muted">
        {formation ? `${teamName} · ${formation}` : teamName} ·{" "}
        {players.filter((player) => player.player_id !== null).length} predicted
        starters
      </p>
      <ol
        className={`lineup-list${listHidden ? " sr-only" : ""}`}
        aria-label={`${teamName} predicted XI`}
      >
        {players.map((player, index) => (
          <li key={`${player.player_id ?? "empty"}-${index}`}>
            <span className="lineup-slot">{player.slot ?? player.grid ?? "—"}</span>
            <span className="lineup-role">{player.role_code ?? "—"}</span>
            {player.player_id === null ? (
              <span className="muted">No eligible player</span>
            ) : (
              <PlayerLink
                name={player.name ?? `Player ${player.player_id}`}
                href={player.href}
              />
            )}
            <span className="muted">
              {player.starts ?? 0} starts · {player.minutes ?? 0} mins · form{" "}
              {Math.round((player.form ?? 0) * 100)} · rating{" "}
              {player.recent_rating ?? "—"}
            </span>
            <span className={`lineup-confidence confidence-${player.confidence || "unknown"}`}>
              {player.confidence || "unknown"}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
