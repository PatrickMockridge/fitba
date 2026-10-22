import { FormStrip } from "@/components/FormStrip";
import { formatDate, type FormBlock, type FormRecord } from "@/lib/data";

function recordLine(record: FormRecord) {
  return `${record.won}W ${record.drawn}D ${record.lost}L · ${record.points} pts · ${record.ppg ?? "—"} PPG`;
}

function SplitTable({ block }: { block: FormBlock }) {
  const rows = [
    { label: "Overall", value: block.season_record },
    { label: "Home", value: block.home },
    { label: "Away", value: block.away },
  ];
  return (
    <div className="table-wrap">
      <table className="league-table compact split-table">
        <thead>
          <tr>
            <th>Split</th>
            <th className="num">P</th>
            <th className="num">W-D-L</th>
            <th className="num">Pts</th>
            <th className="num">PPG</th>
            <th className="num">GF</th>
            <th className="num">GA</th>
            <th className="num">Shots</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td>{row.label}</td>
              <td className="num">{row.value.played}</td>
              <td className="num">
                {row.value.won}-{row.value.drawn}-{row.value.lost}
              </td>
              <td className="num">{row.value.points}</td>
              <td className="num">{row.value.ppg ?? "—"}</td>
              <td className="num">{row.value.gf}</td>
              <td className="num">{row.value.ga}</td>
              <td className="num">
                {row.value.shots_for_pm ?? "—"}/
                {row.value.shots_against_pm ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TeamForm({
  name,
  block,
  isAberdeen = false,
}: {
  name: string;
  block: FormBlock;
  isAberdeen?: boolean;
}) {
  const competition =
    typeof block.sample.competition_name === "string"
      ? block.sample.competition_name
      : "League";
  return (
    <div className={`form-team${isAberdeen ? " is-aberdeen" : ""}`}>
      <div className="form-team-head">
        <div>
          <p className="eyebrow">{competition}</p>
          <h3>{name}</h3>
        </div>
        <FormStrip form={block.form} />
      </div>
      <p className="form-record">{recordLine(block.recent)}</p>
      <ul className="form-match-list">
        {block.matches.map((match, index) => (
          <li key={`${match.match_id ?? match.date}-${index}`}>
            <span className="match-date">{formatDate(match.date)}</span>
            <span className="match-venue">{match.venue}</span>
            <span className="match-opponent">
              {match.opponent_name ?? "Unknown"}
            </span>
            <span className={`result-dot result-${(match.result ?? "").toLowerCase()}`}>
              {match.result ?? "?"}
            </span>
            <span className="match-score">
              {match.gf}–{match.ga}
            </span>
          </li>
        ))}
      </ul>
      <SplitTable block={block} />
      <p className="fine-print">{block.note}</p>
    </div>
  );
}

export function FormGuide({
  aberdeenName,
  opponentName,
  aberdeen,
  opponent,
  aberdeenFirst,
  contract,
}: {
  aberdeenName: string;
  opponentName: string;
  aberdeen: FormBlock;
  opponent: FormBlock;
  aberdeenFirst: boolean;
  contract?: string;
}) {
  const first = aberdeenFirst
    ? { name: aberdeenName, block: aberdeen, isAberdeen: true }
    : { name: opponentName, block: opponent, isAberdeen: false };
  const second = aberdeenFirst
    ? { name: opponentName, block: opponent, isAberdeen: false }
    : { name: aberdeenName, block: aberdeen, isAberdeen: true };
  return (
    <section className="card form-guide" data-contract={contract}>
      <div className="section-head">
        <div>
          <p className="eyebrow">League form</p>
          <h2>Form guide</h2>
        </div>
        <span className="badge badge-neutral">Last five · home and away</span>
      </div>
      <div className="form-guide-grid">
        <TeamForm
          name={first.name}
          block={first.block}
          isAberdeen={first.isAberdeen}
        />
        <TeamForm
          name={second.name}
          block={second.block}
          isAberdeen={second.isAberdeen}
        />
      </div>
    </section>
  );
}
