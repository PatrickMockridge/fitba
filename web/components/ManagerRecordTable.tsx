import type { HistoryManagerRecord } from "@/lib/data";

function shortDate(value: string | null | undefined) {
  if (!value) return "—";
  return value.slice(0, 10);
}

export function ManagerRecordTable({
  records,
  empty = "No manager records are available.",
}: {
  records: HistoryManagerRecord[];
  empty?: string;
}) {
  if (!records.length) return <p className="muted">{empty}</p>;
  return (
    <div className="table-wrap">
      <table className="league-table compact">
        <caption className="fine-print">
          Manager league records with interim spells kept separate.
        </caption>
        <thead>
          <tr>
            <th scope="col">Manager</th>
            <th scope="col">Dates</th>
            <th scope="col" className="num">
              Pld
            </th>
            <th scope="col">W-D-L</th>
            <th scope="col" className="num">
              GF
            </th>
            <th scope="col" className="num">
              GA
            </th>
            <th scope="col" className="num">
              Pts
            </th>
            <th scope="col" className="num">
              PPG
            </th>
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={record.stint_id ?? `${record.name}-${index}`}>
              <td>
                {record.name}
                {record.interim ? <span className="badge badge-warn">Interim</span> : null}
              </td>
              <td className="fine-print">
                {shortDate(record.start)} – {record.end ? shortDate(record.end) : "present"}
              </td>
              <td className="num">{record.played}</td>
              <td>
                {record.won}-{record.drawn}-{record.lost}
              </td>
              <td className="num">{record.gf}</td>
              <td className="num">{record.ga}</td>
              <td className="num strong">{record.points}</td>
              <td className="num">{record.ppg?.toFixed(2) ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
