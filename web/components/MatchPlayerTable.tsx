import type { FixtureDocument } from "@/lib/data";

function n(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
}

export function MatchPlayerTable({
  players,
}: {
  players: FixtureDocument["player_stats"];
}) {
  return (
    <section
      className="card match-player-table"
      data-contract="match.player-stats"
      data-team-split="aberdeen-opponent"
    >
      <div className="section-head">
        <div>
          <p className="eyebrow">Player stats</p>
          <h2>Provider match ratings and output</h2>
        </div>
      </div>
      {players.length ? (
        <div className="table-wrap">
          <table className="league-table">
            <caption className="fine-print">
              Player match statistics with Aberdeen highlighted in red.
            </caption>
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col">Team</th>
                <th scope="col" className="num">
                  Rating
                </th>
                <th scope="col" className="num">
                  Min
                </th>
                <th scope="col" className="num">
                  G
                </th>
                <th scope="col" className="num">
                  A
                </th>
                <th scope="col" className="num">
                  Sh
                </th>
                <th scope="col" className="num">
                  SoT
                </th>
                <th scope="col" className="num">
                  Accurate passes
                </th>
                <th scope="col" className="num">
                  Tackles
                </th>
                <th scope="col" className="num">
                  Duels
                </th>
                <th scope="col" className="num">
                  Cards
                </th>
              </tr>
            </thead>
            <tbody>
              {players.map((player, index) => (
                <tr
                  key={`${player.player_id ?? index}-${player.team_id ?? "team"}`}
                  data-team={
                    player.is_aberdeen === true
                      ? "aberdeen"
                      : player.is_aberdeen === false
                        ? "opponent"
                        : "unknown"
                  }
                >
                  <td>{player.player_name ?? "Unknown"}</td>
                  <td>{player.team_name ?? "Team unknown"}</td>
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
