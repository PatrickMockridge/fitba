import type { ScoutingBoard } from "@/lib/data";
import { formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";

const STATUS_LABEL: Record<string, string> = {
  below: "Below cohort",
  at: "At cohort",
  above: "Above cohort",
  insufficient: "Insufficient data",
};

const READING_LABEL: Record<string, string> = {
  structural: "Structural",
  cover: "Cover",
  hold: "Hold",
  none: "No measured gap",
  insufficient: "Insufficient data",
};

function readingClass(reading: string): string {
  if (reading === "structural") return "badge-negative";
  if (reading === "cover") return "badge-warn";
  if (reading === "hold") return "badge-warn";
  if (reading === "none") return "badge-ok";
  return "badge-neutral";
}

function availabilitySummary(family: ScoutingBoard["families"][number]): string {
  if (!family.layer0.length) return "No verified availability entry";
  return family.layer0
    .map((player) => `${player.name} ${player.availability.status}`)
    .join(" · ");
}

export function ScoutingWeaknessTable({ board }: { board: ScoutingBoard }) {
  return (
    <>
      <div className="table-wrap">
        <table className="league-table compact">
          <caption className="fine-print">
            Aberdeen&apos;s competitive provider rating by role family, compared with the
            Scottish Premiership role cohort (Aberdeen excluded). A percentile is relative to
            that cohort, not a verdict. The reading uses verified availability only.
          </caption>
          <thead>
            <tr>
              <th scope="col">Role family</th>
              <th className="num" scope="col">Players</th>
              <th className="num" scope="col">Minutes</th>
              <th className="num" scope="col">Aberdeen rating</th>
              <th className="num" scope="col">Cohort median</th>
              <th className="num" scope="col">Percentile</th>
              <th scope="col">Availability</th>
              <th scope="col">Reading</th>
            </tr>
          </thead>
          <tbody>
            {board.families.map((family) => (
              <tr key={family.family}>
                <td className="strong">{family.label}</td>
                <td className="num">{formatInteger(family.player_count)}</td>
                <td className="num">{formatInteger(family.minutes)}</td>
                <td className="num">
                  {family.average_rating === null ? "—" : formatDecimal(family.average_rating)}
                </td>
                <td className="num" data-contract-indicator="confidence">
                  {family.cohort.median === null ? "—" : formatDecimal(family.cohort.median)}
                  <span className="muted"> · n={formatInteger(family.cohort.n)}</span>
                </td>
                <td className="num">
                  {family.rating_percentile === null
                    ? "—"
                    : formatPercentValue(family.rating_percentile, 1)}
                </td>
                <td data-contract-indicator="availability">{availabilitySummary(family)}</td>
                <td>
                  <span className={`badge ${readingClass(family.reading)}`}>
                    {READING_LABEL[family.reading] ?? family.reading}
                  </span>
                  <span className="muted"> {STATUS_LABEL[family.status] ?? family.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        The model cannot separate selection, availability and quality. A role family below the
        cohort with a first-choice absentee is read as cover, not as a replacement. A family
        without a qualifying cohort is not ranked.
      </p>
    </>
  );
}
