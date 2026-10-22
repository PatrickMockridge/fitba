import { Fragment } from "react";
import Link from "next/link";
import { FormStrip } from "@/components/FormStrip";
import type { Cutoff, TableRow } from "@/lib/data";

export function LeagueTable({
  rows,
  highlightTeamId,
  compact = false,
  cutoffs = [],
  caption = "League table: position, played, won, drawn, lost, goals for and against, goal difference, points and form.",
}: {
  rows: TableRow[];
  highlightTeamId?: string;
  compact?: boolean;
  cutoffs?: Cutoff[];
  caption?: string;
}) {
  const columnCount = compact ? 10 : 11;
  const cutoffsByPosition = new Map(
    cutoffs.map((cutoff) => [cutoff.after_position, cutoff]),
  );
  return (
    <div className="table-wrap">
      <table className="league-table">
        <caption className="fine-print">{caption}</caption>
        <thead>
          <tr>
            <th scope="col" className="num">
              #
            </th>
            <th scope="col">Club</th>
            <th scope="col" className="num">
              P
            </th>
            <th scope="col" className="num">
              W
            </th>
            <th scope="col" className="num">
              D
            </th>
            <th scope="col" className="num">
              L
            </th>
            <th scope="col" className="num">
              GF
            </th>
            <th scope="col" className="num">
              GA
            </th>
            <th scope="col" className="num">
              GD
            </th>
            <th scope="col" className="num">
              Pts
            </th>
            {compact ? null : <th scope="col">Form</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isAberdeen = row.team_id === highlightTeamId;
            const cutoff = cutoffsByPosition.get(row.position);
            return (
              <Fragment key={row.team_id}>
                <tr className={isAberdeen ? "is-highlight" : undefined}>
                  <td className="num">{row.position}</td>
                  <td>
                    {row.team_id === "sco:aberdeen" ? (
                      <Link href="/matchday/">{row.team_name}</Link>
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
                {cutoff ? (
                  <tr className={`cutoff cutoff-${cutoff.kind}`}>
                    <td colSpan={columnCount}>
                      <span className="cutoff-label">{cutoff.label}</span>
                      {cutoff.note ? <span className="cutoff-note">{cutoff.note}</span> : null}
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
