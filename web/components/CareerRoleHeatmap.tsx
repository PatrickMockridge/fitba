import type { CareerRole } from "@/lib/data";
import { slotColor } from "@/lib/roles";

function rgba(hex: string, alpha: number): string {
  const value = hex.replace("#", "");
  const red = parseInt(value.slice(0, 2), 16);
  const green = parseInt(value.slice(2, 4), 16);
  const blue = parseInt(value.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${Math.min(0.88, Math.max(0.08, alpha))})`;
}

export function CareerRoleHeatmap({ career }: { career: CareerRole }) {
  const slots = career.slot_definitions?.length
    ? career.slot_definitions
    : career.slots;
  if (!slots.length) return null;
  const rows = [
    ...career.seasons.map((season) => ({
      key: season.season,
      label: season.season,
      starts: season.starts_with_role,
      values: Object.fromEntries(season.slots.map((slot) => [slot.slot, slot])),
    })),
    {
      key: "career",
      label: "Career",
      starts: career.starts_with_role,
      values: Object.fromEntries(career.slots.map((slot) => [slot.slot, slot])),
    },
  ];

  return (
    <div className="table-wrap">
      <table className="league-table compact role-heatmap">
<caption className="fine-print">Career starts by role family and season.</caption>
        <thead>
          <tr>
            <th>Season</th>
            {slots.map((slot) => (
              <th key={slot.slot} className="num" title={slot.label}>
                {slot.fm}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <td className="role-heat-season">
                {row.label}
                <span className="fine-print"> · {row.starts}</span>
              </td>
              {slots.map((slot) => {
                const value = row.values[slot.slot];
                const share = value?.share ?? 0;
                const starts = value?.starts ?? 0;
                const text = starts >= 3 ? `${Math.round(share * 100)}%` : starts ? `n=${starts}` : "—";
                return (
                  <td
                    key={slot.slot}
                    className="num role-heat-cell"
                    style={{
                      backgroundColor: starts
                        ? rgba(slotColor(slot.groups), share)
                        : undefined,
                    }}
                    title={
                      starts
                        ? `${slot.label}: ${starts} starts, ${Math.round(share * 100)}%`
                        : `${slot.label}: no starts`
                    }
                  >
                    {text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
