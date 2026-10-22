import type { ThemeDepthGroup, ThemePlayer } from "@/lib/data";

function categoryLabel(category: string | null | undefined) {
  if (!category) return "—";
  return category.replaceAll("_", " ");
}

function groupLabel(group: string) {
  return group === "FB/WB" ? "Full-backs / wing-backs" : "Centre-backs";
}

export function DepthChart({
  groups,
  curatedNotes,
}: {
  groups: ThemeDepthGroup[];
  curatedNotes: Array<Record<string, unknown>>;
}) {
  return (
    <div className="depth-chart">
      <div className="section-head">
        <div>
          <p className="eyebrow">Minutes, rotation and arrivals</p>
          <h3>Defensive depth</h3>
        </div>
        <span className="badge badge-neutral">Curated availability</span>
      </div>
      <div className="stat-row four">
        {groups.map((group) => (
          <div className="stat-tile" key={group.group}>
            <span className="stat-label">{groupLabel(group.group)}</span>
            <span className="stat-value">{group.players}</span>
            <span className="stat-note">
              {group.starters} starter minutes · {group.players_with_3_starts} with
              3+ starts · top share {group.top_share ?? "—"}
            </span>
          </div>
        ))}
      </div>
      {groups.map((group) => (
        <div className="table-wrap" key={group.group}>
          <table className="league-table compact">
            <thead>
              <tr>
                <th>{groupLabel(group.group)}</th>
                <th>Role</th>
                <th>Category</th>
                <th className="num">Starts</th>
                <th className="num">Minutes</th>
                <th className="num">Sub apps</th>
                <th className="num">Named bench</th>
                <th>Arrival</th>
              </tr>
            </thead>
            <tbody>
              {group.items.map((player: ThemePlayer) => (
                <tr key={`${group.group}-${player.player_id}-${player.name}`}>
                  <td className="strong">{player.name ?? "Unknown"}</td>
                  <td>{player.role_family?.replaceAll("_", " ") ?? "—"}</td>
                  <td>{categoryLabel(player.category)}</td>
                  <td className="num">{player.starts ?? 0}</td>
                  <td className="num">{player.minutes ?? 0}</td>
                  <td className="num">{player.sub_apps ?? 0}</td>
                  <td className="num">{player.bench_named ?? 0}</td>
                  <td>{player.arrival ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="fine-print">
            {group.concentration === "high"
              ? "Minutes are concentrated at the top of this group."
              : "Minutes are spread across the group."}{" "}
            {group.thin_rotation
              ? "Fewer than three players have three or more starts."
              : "At least three players have three or more starts."}
          </p>
        </div>
      ))}
      {curatedNotes.length ? (
        <div className="mini-block">
          <p className="eyebrow">Curated note</p>
          {curatedNotes.map((note) => (
            <p className="fine-print" key={String(note.player_id)}>
              <strong>{String(note.name ?? "Player")}:</strong>{" "}
              {String(note.note ?? "")} <span className="muted">(curated)</span>
            </p>
          ))}
        </div>
      ) : null}
      <p className="fine-print">
        Minutes are not proof of trust; the data cannot distinguish selection
        from curated availability. Provider “injured” flags are not team news.
        Unknown stays unknown.
      </p>
    </div>
  );
}
