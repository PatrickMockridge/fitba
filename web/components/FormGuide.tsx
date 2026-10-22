import { FormStrip } from "@/components/FormStrip";
import { TableFrame, Th } from "@/components/TableFrame";
import { formatDate, type FormBlock, type FormRecord } from "@/lib/data";

function recordLine(record: FormRecord) {
  return `${record.won}W ${record.drawn}D ${record.lost}L · ${record.points} pts · ${record.ppg ?? "—"} PPG`;
}

function SplitRow({ team, split, record }: { team: string; split: string; record: FormRecord }) {
  return (
    <tr>
      <td>{split}</td>
      <td>{team}</td>
      <td className="num">{record.played}</td>
      <td className="num">
        {record.won}-{record.drawn}-{record.lost}
      </td>
      <td className="num">{record.points}</td>
      <td className="num">{record.ppg ?? "—"}</td>
    </tr>
  );
}

export function FormGuide({
  aberdeenName,
  opponentName,
  aberdeen,
  opponent,
}: {
  aberdeenName: string;
  opponentName: string;
  aberdeen: FormBlock;
  opponent: FormBlock;
}) {
  const matches = [
    ...aberdeen.matches.map((match) => ({ ...match, team: aberdeenName })),
    ...opponent.matches.map((match) => ({ ...match, team: opponentName })),
  ].sort((a, b) => (a.date < b.date ? 1 : -1));

  return (
    <section className="section">
      <div className="section-head">
        <h2>How is each side playing?</h2>
        <span className="muted">League only</span>
      </div>

      <div className="grid two-col">
        <div>
          <h3>{aberdeenName}</h3>
          <FormStrip form={aberdeen.form} />
          <p className="muted">{recordLine(aberdeen.recent)}</p>
        </div>
        <div>
          <h3>{opponentName}</h3>
          <FormStrip form={opponent.form} />
          <p className="muted">{recordLine(opponent.recent)}</p>
        </div>
      </div>

      <TableFrame label="Form splits" caption="League form splits for both teams">
        <thead>
          <tr>
            <Th>Split</Th>
            <Th>Team</Th>
            <Th className="num">P</Th>
            <Th className="num">W-D-L</Th>
            <Th className="num">Pts</Th>
            <Th className="num">PPG</Th>
          </tr>
        </thead>
        <tbody>
          <SplitRow team={aberdeenName} split="Overall" record={aberdeen.season_record} />
          <SplitRow team={opponentName} split="Overall" record={opponent.season_record} />
          <SplitRow team={aberdeenName} split="Home" record={aberdeen.home} />
          <SplitRow team={opponentName} split="Home" record={opponent.home} />
          <SplitRow team={aberdeenName} split="Away" record={aberdeen.away} />
          <SplitRow team={opponentName} split="Away" record={opponent.away} />
        </tbody>
      </TableFrame>

      <details className="page-legend">
        <summary>Last five matches</summary>
        <div className="page-legend-body">
          <TableFrame label="Last five matches" caption="Last five league matches for both teams">
            <thead>
              <tr>
                <Th>Team</Th>
                <Th>Date</Th>
                <Th>H/A</Th>
                <Th>Opponent</Th>
                <Th>Result</Th>
                <Th className="num">Score</Th>
              </tr>
            </thead>
            <tbody>
              {matches.map((match, index) => (
                <tr key={`${match.team}-${match.match_id ?? match.date}-${index}`}>
                  <td>{match.team}</td>
                  <td>{formatDate(match.date)}</td>
                  <td>{match.venue ?? "—"}</td>
                  <td>{match.opponent_name ?? "Unknown"}</td>
                  <td>{match.result ?? "—"}</td>
                  <td className="num">
                    {match.gf}–{match.ga}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableFrame>
        </div>
      </details>
    </section>
  );
}
