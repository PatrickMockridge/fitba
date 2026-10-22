import Link from "next/link";
import type { CupGroup } from "@/lib/data";

export function CupGroupTable({
  group,
  highlightTeamId,
}: {
  group: CupGroup;
  highlightTeamId?: string;
}) {
  return (
    <section className="cup-group">
      <div className="cup-group-head">
        <h3>{group.id}</h3>
        <span className="muted">{group.rows.length} teams</span>
      </div>
      <div className="table-wrap">
        <table className="league-table compact cup-group-table">
          <caption className="fine-print">
            {group.id} table with group-stage points and shoot-out bonus.
          </caption>
          <thead>
            <tr>
              <th className="num">#</th>
              <th>Club</th>
              <th className="num">P</th>
              <th className="num" title="Wins">W</th>
              <th className="num" title="Shoot-out wins">PW</th>
              <th className="num" title="Shoot-out losses">PL</th>
              <th className="num">L</th>
              <th className="num">GF</th>
              <th className="num">GA</th>
              <th className="num">GD</th>
              <th className="num">Pts</th>
            </tr>
          </thead>
          <tbody>
            {group.rows.map((row) => (
              <tr
                key={row.team_id}
                className={row.team_id === highlightTeamId ? "is-highlight" : undefined}
              >
                <td className="num">{row.position}</td>
                <td>
                  {row.team_id === "sco:aberdeen" ? (
                    <Link href="/matchday/">{row.team_name}</Link>
                  ) : (
                    row.team_name
                  )}
                </td>
                <td className="num">{row.played}</td>
                <td className="num">{row.won}</td>
                <td className="num">{row.shootout_won}</td>
                <td className="num">{row.shootout_lost}</td>
                <td className="num">{row.lost}</td>
                <td className="num">{row.gf}</td>
                <td className="num">{row.ga}</td>
                <td className="num">{row.gd > 0 ? `+${row.gd}` : row.gd}</td>
                <td className="num strong">{row.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
