import Link from "next/link";
import { FormStrip } from "@/components/FormStrip";
import type { TableRow } from "@/lib/data";

export function LeagueTable({
  rows,
  highlightTeamId,
  compact = false,
}: {
  rows: TableRow[];
  highlightTeamId?: string;
  compact?: boolean;
}) {
  return (
    <div className="table-wrap">
      <table className="league-table">
        <thead>
          <tr>
            <th className="num">#</th>
            <th>Club</th>
            <th className="num">P</th>
            <th className="num">W</th>
            <th className="num">D</th>
            <th className="num">L</th>
            <th className="num">GF</th>
            <th className="num">GA</th>
            <th className="num">GD</th>
            <th className="num">Pts</th>
            {compact ? null : <th>Form</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isAberdeen = row.team_id === highlightTeamId;
            return (
              <tr key={row.team_id} className={isAberdeen ? "is-highlight" : undefined}>
                <td className="num">{row.position}</td>
                <td>
                  {row.team_id === "sco:aberdeen" ? (
                    <Link href="/clubs/aberdeen/">{row.team_name}</Link>
                  ) : (
                    row.team_name
                  )}
                  {row.deduction > 0 ? (
                    <span className="deduction" title={`${row.deduction}-point deduction`}>
                      −{row.deduction}
                    </span>
                  ) : null}
                </td>
                <td className="num">{row.played}</td>
                <td className="num">{row.won}</td>
                <td className="num">{row.drawn}</td>
                <td className="num">{row.lost}</td>
                <td className="num">{row.gf}</td>
                <td className="num">{row.ga}</td>
                <td className="num">{row.gd > 0 ? `+${row.gd}` : row.gd}</td>
                <td className="num strong">{row.points}</td>
                {compact ? null : (
                  <td>
                    <FormStrip form={row.form} />
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
