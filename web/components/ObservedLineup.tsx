import type { FixtureLineup } from "@/lib/data";

function playerName(player: FixtureLineup["starters"][number]): string {
  const number = player.shirt_number === null ? "" : `${player.shirt_number} `;
  return `${number}${player.player_name ?? "Unknown player"}`;
}

export function ObservedLineup({ lineup }: { lineup: FixtureLineup | null }) {
  if (!lineup) {
    return (
      <div className="match-lineup" data-contract="match.lineup">
        <p className="fine-print">The lineup for this team is unavailable.</p>
      </div>
    );
  }
  return (
    <div className="match-lineup" data-contract="match.lineup">
      <div className="section-head">
        <div>
          <p className="eyebrow">{lineup.team_name}</p>
          <h3>{lineup.formation ?? "Formation unknown"}</h3>
        </div>
        <span className="badge badge-neutral">{lineup.coach_name ?? "Coach unknown"}</span>
      </div>
      <div className="table-wrap">
        <table className="league-table">
          <thead>
            <tr>
              <th>Starter</th>
              <th>Role</th>
              <th className="num">Min</th>
            </tr>
          </thead>
          <tbody>
            {lineup.starters.map((player, index) => (
              <tr key={`${player.player_id ?? index}-start`}>
                <td>{playerName(player)}</td>
                <td>{player.role ?? player.position ?? "—"}</td>
                <td className="num">{player.minutes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h4>Substitutes</h4>
      <ul className="plain-list">
        {lineup.substitutes.map((player, index) => (
          <li key={`${player.player_id ?? index}-sub`}>
            {playerName(player)}
            {player.on_minute !== null && player.on_minute !== undefined
              ? ` · on ${player.on_minute}'`
              : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
