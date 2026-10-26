import Link from "next/link";
import { AvailabilityBadge } from "@/components/AvailabilityBadge";
import { TableFrame } from "@/components/TableFrame";
import type { ScoutingLayerZero, SquadPlayer } from "@/lib/data";
import { FAMILY_LABELS, FAMILY_ORDER } from "@/lib/roles";
import { formatInteger } from "@/lib/format";

type DepthRow = {
  key: string;
  family: string;
  familyLabel: string;
  name: string;
  href: string | null;
  role: string;
  minutes: number | null;
  availability: string | null;
  availabilityNote: string | null;
  status: string;
  ledgerOnly: boolean;
};

const FAMILIES = Object.keys(FAMILY_LABELS).sort(
  (left, right) => (FAMILY_ORDER[left] ?? 99) - (FAMILY_ORDER[right] ?? 99),
);

function playerFamily(player: SquadPlayer): string {
  for (const candidate of [
    player.display_role?.family,
    player.role?.family,
    player.career_role?.dominant?.family,
  ]) {
    if (candidate && FAMILY_LABELS[candidate]) return candidate;
  }
  return "unknown";
}

function playerRole(player: SquadPlayer): string {
  if (player.display_role?.label) return player.display_role.label;
  if (player.role?.primary) return player.role.primary;
  return "Role unknown";
}

function playerMinutes(player: SquadPlayer): number | null {
  if (player.playing_time?.coverage === "unavailable") return null;
  return player.playing_time?.minutes ?? null;
}

function statusLabel(player: SquadPlayer): string {
  if (player.status === "loan_out") {
    return player.loan?.club ? `On loan · ${player.loan.club}` : "On loan out";
  }
  if (player.squad_member) return "Squad";
  return player.status || "—";
}

export function DepthChart({
  players,
  ledger = [],
}: {
  players: SquadPlayer[];
  ledger?: ScoutingLayerZero[];
}) {
  const squadIds = new Set(players.map((player) => player.player_id));
  const rows: DepthRow[] = players.map((player) => {
    const family = playerFamily(player);
    return {
      key: `squad-${player.player_id}`,
      family,
      familyLabel: FAMILY_LABELS[family] ?? family,
      name: player.name,
      href: player.href ?? null,
      role: playerRole(player),
      minutes: playerMinutes(player),
      availability: player.availability?.status ?? "unknown",
      availabilityNote: player.availability?.note ?? null,
      status: statusLabel(player),
      ledgerOnly: false,
    };
  });
  for (const entry of ledger) {
    if (squadIds.has(entry.player_id)) continue;
    const family = entry.family && FAMILY_LABELS[entry.family] ? entry.family : "unknown";
    rows.push({
      key: `ledger-${entry.player_id}`,
      family,
      familyLabel: FAMILY_LABELS[family] ?? family,
      name: entry.name,
      href: null,
      role: entry.role_label ?? "Role unknown",
      minutes: entry.minutes ?? null,
      availability: entry.status || "unknown",
      availabilityNote: entry.note ?? null,
      status: "Ledger only",
      ledgerOnly: true,
    });
  }

  return (
    <section className="section" data-contract="squad.depth-chart">
      <div className="section-head">
        <div>
          <p className="eyebrow">Depth by role</p>
          <h2>Role-family depth chart</h2>
        </div>
        <span className="badge badge-neutral">Measured minutes, not a ranking</span>
      </div>
      <p>
        Every official squad player once, grouped by the ten role families. Within
        a family, players are ordered by measured all-competition minutes; an
        unavailable player is not dropped and an unknown availability is not
        treated as fit. There is no quality score and no drop-off claim.
      </p>
      <TableFrame label="Role-family depth chart" sticky={false}>
        <table className="league-table depth-chart">
          <caption className="fine-print">
            Role-family depth from the official squad and the verified availability
            ledger. Minutes are all competitions; unknown minutes are shown as —.
          </caption>
          <thead>
            <tr>
              <th scope="col">Family</th>
              <th scope="col">Player</th>
              <th scope="col">Role</th>
              <th scope="col">Mins (all)</th>
              <th scope="col">Availability</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {FAMILIES.map((family) => {
              const familyRows = rows
                .filter((row) => row.family === family)
                .sort((left, right) => {
                  const leftMinutes = left.minutes ?? -1;
                  const rightMinutes = right.minutes ?? -1;
                  if (leftMinutes !== rightMinutes) return rightMinutes - leftMinutes;
                  return left.name.localeCompare(right.name);
                });
              if (!familyRows.length) {
                return (
                  <tr key={`empty-${family}`} className="depth-empty">
                    <td>{FAMILY_LABELS[family] ?? family}</td>
                    <td>No player with a measured role in this family.</td>
                    <td>—</td>
                    <td>—</td>
                    <td>—</td>
                    <td>—</td>
                  </tr>
                );
              }
              return familyRows.map((row) => (
                <tr key={row.key} data-depth-ledger={row.ledgerOnly || undefined}>
                  <td>{row.familyLabel}</td>
                  <td>
                    {row.href ? <Link href={row.href}>{row.name}</Link> : row.name}
                  </td>
                  <td>{row.role}</td>
                  <td>{row.minutes === null ? "—" : formatInteger(row.minutes)}</td>
                  <td>
                    <AvailabilityBadge
                      status={row.availability}
                      note={row.availabilityNote}
                      compact
                    />
                  </td>
                  <td>{row.status}</td>
                </tr>
              ));
            })}
          </tbody>
        </table>
      </TableFrame>
      <p className="fine-print" data-contract-indicator="unknown">
        Availability comes from the verified ledger only; the provider injury feed is
        not used. A row marked unknown has no verified entry, which is not the same
        as available. Loanees out stay in the squad record and are labelled with
        their loan club.
      </p>
    </section>
  );
}
