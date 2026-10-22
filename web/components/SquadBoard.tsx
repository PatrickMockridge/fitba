"use client";

import { useMemo, useState } from "react";
import { CardMark } from "@/components/CardMark";
import { PlayerLink } from "@/components/PlayerLink";
import { RoleInferenceDialog } from "@/components/RoleInference";
import type { SquadPlayer } from "@/lib/data";
import {
  FAMILY_ORDER,
  SLOT_ORDER,
  familyBroadGroups,
  familyLabel,
  familySide,
} from "@/lib/roles";

type GroupFilter = "all" | "goalkeeper" | "defender" | "midfielder" | "attacker";
type SideFilter = "all" | "left" | "centre" | "right";
type StatusFilter = "all" | "squad" | "loan_out" | "loan_in";

const STATUS_ORDER: Record<string, number> = { squad: 0, loan_in: 1, loan_out: 2 };

function value(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
}

function statusBadge(player: SquadPlayer) {
  if (player.status === "loan_out") {
    return <span className="badge badge-warn">On loan · {player.loan?.club ?? "club unknown"}</span>;
  }
  if (player.status === "loan_in") {
    return (
      <span className="badge badge-warn">On loan from {player.loan?.club ?? "club unknown"}</span>
    );
  }
  return <span className="badge badge-ok">Squad</span>;
}

function displayFamily(player: SquadPlayer): string {
  return player.display_role?.family ?? player.role?.family ?? "unknown";
}

function playerSlots(player: SquadPlayer): Array<{
  slot?: string;
  groups: string[];
  side: string | null;
}> {
  const slots = player.career_role?.eligibility ?? [];
  if (slots.length) {
    return slots.map((slot) => ({
      slot: slot.slot,
      groups: slot.groups,
      side: slot.side,
    }));
  }
  const family = displayFamily(player);
  return [
    {
      groups: familyBroadGroups(family),
      side: familySide(family, player.display_role?.side ?? player.role?.side),
    },
  ];
}

function primarySlotOrder(player: SquadPlayer): number {
  const slot = player.career_role?.primary_slot?.slot;
  if (slot && slot in SLOT_ORDER) return SLOT_ORDER[slot];
  return (FAMILY_ORDER[displayFamily(player)] ?? 99) + 100;
}

function defensive(player: SquadPlayer): boolean {
  const family = displayFamily(player);
  if (family !== "unknown") {
    return [
      "goalkeeper",
      "centre_back",
      "full_back",
      "wing_back",
      "defensive_midfield",
    ].includes(family);
  }
  return player.position_group === "GK" || player.position_group === "DEF";
}

function roleLabel(player: SquadPlayer): string {
  if (player.display_role?.label) return player.display_role.label;
  if (player.role?.primary) return player.role.primary;
  return player.position ?? player.position_group ?? "—";
}

function roleTitle(player: SquadPlayer): string {
  const career = player.career_role;
  const current = player.role;
  const parts: string[] = [];
  if (career?.primary_slot) {
    parts.push(
      `Career: ${career.fm_label || career.primary_slot.fm} ` +
        `(${career.primary_slot.starts} starts, ${career.seasons_with_role} seasons)`,
    );
  } else if (career?.top_families?.length) {
    parts.push(
      `Career: ${career.top_families
        .slice(0, 2)
        .map((row) => `${familyLabel(row.family)} ${Math.round(row.share * 100)}%`)
        .join(", ")}`,
    );
  }
  if (career?.secondary_slots?.length) {
    parts.push(
      `Also: ${career.secondary_slots
        .slice(0, 3)
        .map((row) => `${row.fm} (${Math.round(row.share * 100)}%)`)
        .join(", ")}`,
    );
  }
  if (career?.stretch_slots?.length) {
    parts.push(
      `Stretch: ${career.stretch_slots
        .slice(0, 3)
        .map((row) => row.fm)
        .join(", ")}`,
    );
  }
  if (current?.primary) {
    parts.push(
      `Aberdeen current: ${current.primary} (${current.starts_with_role}/${current.starts_total})`,
    );
  }
  if (player.display_role?.source === "aberdeen_override") {
    parts.push("Showing the current Aberdeen role because it is clearly different.");
  } else if (player.display_role?.source === "career") {
    parts.push("Showing the career role.");
  } else if (player.display_role?.source === "career_low_evidence") {
    parts.push("Showing a provisional career role.");
  }
  if (parts.length) return parts.join(" · ");
  if (player.status === "loan_out") return "No Aberdeen starting-XI role observed";
  return "No starting-XI role observed; showing the squad position";
}

export function SquadBoard({ players }: { players: SquadPlayer[] }) {
  const [group, setGroup] = useState<GroupFilter>("all");
  const [side, setSide] = useState<SideFilter>("all");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<SquadPlayer | null>(null);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return players
      .filter((player) => {
        const slots = playerSlots(player);
        if (group !== "all" && !slots.some((slot) => slot.groups.includes(group))) {
          return false;
        }
        if (side !== "all" && !slots.some((slot) => slot.side === side)) return false;
        if (status !== "all" && player.status !== status) return false;
        if (
          needle &&
          !`${player.full_name} ${player.name} ${player.display_role?.label ?? ""} ${
            player.career_role?.fm_label ?? ""
          } ${player.role?.fm_label ?? ""}`
            .toLowerCase()
            .includes(needle)
        ) {
          return false;
        }
        return true;
      })
      .sort((left, right) => {
        const statusDelta =
          (STATUS_ORDER[left.status] ?? 9) - (STATUS_ORDER[right.status] ?? 9);
        if (statusDelta !== 0) return statusDelta;
        const slotDelta = primarySlotOrder(left) - primarySlotOrder(right);
        if (slotDelta !== 0) return slotDelta;
        return (left.full_name || left.name).localeCompare(right.full_name || right.name);
      });
  }, [players, group, side, status, query]);

  return (
    <section>
      <div className="board-controls">
        <label>
          Group
          <select value={group} onChange={(event) => setGroup(event.target.value as GroupFilter)}>
            <option value="all">All groups</option>
            <option value="goalkeeper">Goalkeepers</option>
            <option value="defender">Defenders</option>
            <option value="midfielder">Midfielders</option>
            <option value="attacker">Attackers</option>
          </select>
        </label>

        <label>
          Side
          <select value={side} onChange={(event) => setSide(event.target.value as SideFilter)}>
            <option value="all">All sides</option>
            <option value="left">Left</option>
            <option value="centre">Centre</option>
            <option value="right">Right</option>
          </select>
        </label>

        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}>
            <option value="all">Squad and loans</option>
            <option value="squad">Squad only</option>
            <option value="loan_out">On loan out</option>
            <option value="loan_in">On loan in</option>
          </select>
        </label>

        <label>
          Player
          <input
            type="search"
            value={query}
            placeholder="Search name or role"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>

      <p className="fine-print">
        {filtered.length} player{filtered.length === 1 ? "" : "s"} in this view.{" "}
        <strong>Click a player&apos;s position</strong> to see how it was inferred: current
        Aberdeen usage, career clubs and seasons, the FM-style eligibility and any tactical
        context. The Group/Side filters use the full eligibility set, so a full-back or
        wing-back can appear under both defenders and midfielders, a DM is a midfielder, and a
        winger is an attacker. Starts, Sub and Mins are Aberdeen-only and reconstructed from
        lineups and substitution events. G/A, cards and Rating are provider per-competition
        stats. Conc (goals conceded while on the pitch), CS (clean sheets, 60+ minutes) and OG
        (own goals) are reconstructed from events and shown for defensive primary roles only.
      </p>

      <div className="table-wrap">
        <table className="league-table compact squad-table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Role</th>
              <th className="num">Age</th>
              <th>Status</th>
              <th className="num">Starts</th>
              <th className="num">Sub</th>
              <th className="num">Mins</th>
              <th className="num">Conc</th>
              <th className="num">CS</th>
              <th className="num">G</th>
              <th className="num">A</th>
              <th className="num">OG</th>
              <th className="num">
                <CardMark color="yellow" />
              </th>
              <th className="num">
                <CardMark color="red" />
              </th>
              <th className="num">Rating</th>
              <th>Stats</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((player) => {
              const time = player.playing_time;
              const timeShown =
                time && (time.coverage === "available" || time.coverage === "partial")
                  ? time
                  : null;
              return (
                <tr key={player.player_id}>
                  <td>
                    <PlayerLink name={player.full_name || player.name} href={player.href} />
                    {player.availability?.status &&
                    player.availability.status !== "unknown" ? (
                      <span className="badge badge-warn">
                        {" "}
                        {player.availability.status}
                      </span>
                    ) : null}
                  </td>
                  <td>
                    <button
                      className="role-inference-trigger"
                      type="button"
                      title={roleTitle(player)}
                      aria-haspopup="dialog"
                      onClick={() => setSelected(player)}
                    >
                      {roleLabel(player)}
                    </button>
                  </td>
                  <td className="num">{player.age ?? "—"}</td>
                  <td>{statusBadge(player)}</td>
                  <td className="num">{timeShown ? value(timeShown.starts) : "—"}</td>
                  <td className="num">{timeShown ? value(timeShown.sub_apps) : "—"}</td>
                  <td className="num">{timeShown ? value(timeShown.minutes) : "—"}</td>
                  <td className="num">
                    {defensive(player) ? value(player.position_totals?.conceded_on_pitch) : "—"}
                  </td>
                  <td className="num">
                    {defensive(player) ? value(player.position_totals?.clean_sheets) : "—"}
                  </td>
                  <td className="num">{value(player.totals?.goals)}</td>
                  <td className="num">{value(player.totals?.assists)}</td>
                  <td className="num">
                    {defensive(player) ? value(player.position_totals?.own_goals) : "—"}
                  </td>
                  <td className="num">{value(player.totals?.yellow_cards)}</td>
                  <td className="num">{value(player.totals?.red_cards)}</td>
                  <td className="num">
                    {player.totals?.rating === null || player.totals?.rating === undefined
                      ? "—"
                      : player.totals.rating.toFixed(2)}
                  </td>
                  <td>
                    <span
                      className={
                        player.stats_coverage === "available"
                          ? "badge badge-ok"
                          : player.stats_coverage === "partial"
                            ? "badge badge-warn"
                            : "badge badge-neutral"
                      }
                    >
                      {player.stats_coverage}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 ? (
        <p className="muted">No players match these filters.</p>
      ) : null}

      <RoleInferenceDialog player={selected} onClose={() => setSelected(null)} />
    </section>
  );
}
