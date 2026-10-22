import type { ThemePlayer, ThemeShapeGroup } from "@/lib/data";

function groupLabel(group: string) {
  if (group === "two_cb") return "Two centre-backs";
  if (group === "three_cb") return "Three centre-backs";
  return "Shape unknown";
}

function result(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : value;
}

export function ShapeSplitTable({
  groups,
  players,
}: {
  groups: ThemeShapeGroup[];
  players: ThemePlayer[];
}) {
  return (
    <div className="shape-split">
      <div className="section-head">
        <div>
          <p className="eyebrow">Kick-off shape · all competitive fixtures</p>
          <h3>Two vs three centre-backs</h3>
        </div>
        <span className="badge badge-warn">Small sample</span>
      </div>
      <div className="table-wrap">
        <table className="league-table compact">
          <thead>
            <tr>
              <th>Shape</th>
              <th className="num">P</th>
              <th className="num">Record</th>
              <th className="num">Pts/game</th>
              <th className="num">GF/game</th>
              <th className="num">GA/game</th>
              <th className="num">Saves/game</th>
              <th className="num">CB rating</th>
              <th className="num">WB starts</th>
              <th className="num">W starts</th>
              <th className="num">WF bench</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <tr key={group.group}>
                <td className="strong">{groupLabel(group.group)}</td>
                <td className="num">{group.matches}</td>
                <td className="num">{group.record}</td>
                <td className="num">{result(group.points_pg)}</td>
                <td className="num">{result(group.gf_pm)}</td>
                <td className="num">{result(group.ga_pm)}</td>
                <td className="num">{result(group.saves_pm)}</td>
                <td className="num">{result(group.cb_rating)}</td>
                <td className="num">{result(group.wb_starts_pm)}</td>
                <td className="num">{result(group.wf_starts_pm)}</td>
                <td className="num">{result(group.named_bench_wf_pm)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table className="league-table compact">
          <thead>
            <tr>
              <th>Wide / full-back player</th>
              <th>Role</th>
              <th className="num">2-CB starts</th>
              <th className="num">3-CB starts</th>
              <th className="num">Sub minutes</th>
              <th className="num">Named bench</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player) => (
              <tr key={`${player.player_id}-${player.name}`}>
                <td className="strong">{player.name ?? "Unknown"}</td>
                <td>{player.role_family?.replaceAll("_", " ") ?? "—"}</td>
                <td className="num">{player.two_cb_starts ?? 0}</td>
                <td className="num">{player.three_cb_starts ?? 0}</td>
                <td className="num">{player.sub_minutes ?? 0}</td>
                <td className="num">{player.bench_named ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        Kick-off shape only; mid-game switches are not inferred. Named bench and
        substitute minutes are Premiership-only. No channel or cross data is
        available, so the “doubling up in the channels” claim cannot be
        measured.
      </p>
    </div>
  );
}
