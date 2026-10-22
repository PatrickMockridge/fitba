import type { FixtureDocument } from "@/lib/data";

function n(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
}

export function MatchPlayerTable({
  players,
  home,
  away,
  aberdeenIsHome,
}: {
  players: FixtureDocument["player_stats"];
  home: string;
  away: string;
  aberdeenIsHome: boolean;
}) {
  const teamName = (teamId: number | null): string => {
    if (teamId === 252) return "Aberdeen";
    return aberdeenIsHome ? away : home;
  };
  return (
    <section className="card" data-contract="match.player-stats">
      <div className="section-head">
        <div>
          <p className="eyebrow">Player stats</p>
          <h2>Provider match ratings and output</h2>
        </div>
      </div>
      {players.length ? (
        <div className="table-wrap">
          <table className="league-table">
            <thead>
              <tr>
                <th>Player</th>
                <th>Team</th>
                <th className="num">Rating</th>
                <th className="num">Min</th>
                <th className="num">G</th>
                <th className="num">A</th>
                <th className="num">Sh</th>
                <th className="num">SoT</th>
                <th className="num">Accurate passes</th>
                <th className="num">Tackles</th>
                <th className="num">Duels</th>
                <th className="num">Cards</th>
              </tr>
            </thead>
            <tbody>
              {players.map((player, index) => (
                <tr key={`${player.player_id ?? index}-${player.team_id ?? "team"}`}>
                  <td>{player.player_name ?? "Unknown"}</td>
                  <td>{teamName(player.team_id)}</td>
                  <td className="num">{n(player.rating)}</td>
                  <td className="num">{n(player.minutes)}</td>
                  <td className="num">{n(player.goals)}</td>
                  <td className="num">{n(player.assists)}</td>
                  <td className="num">{n(player.shots_total)}</td>
                  <td className="num">{n(player.shots_on)}</td>
                  <td className="num">{n(player.pass_accuracy)}</td>
                  <td className="num">{n(player.tackles)}</td>
                  <td className="num">{n(player.duels_won)}</td>
                  <td className="num">
                    {n(player.yellow_cards)}/{n(player.red_cards)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="fine-print">
          Per-player match statistics are unavailable for this fixture. The
          lineup and event record remain on the page.
        </p>
      )}
      <p className="fine-print">
        Ratings are provider values. They are not position-adjusted and are not
        a verdict on a player.
      </p>
    </section>
  );
}
