"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { CareerRoleHeatmap } from "@/components/CareerRoleHeatmap";
import { RoleMix } from "@/components/RoleMix";
import type { SquadPlayer } from "@/lib/data";
import type { RoleInferenceModel } from "@/lib/player-page";
import { SCOPE_LABELS } from "@/lib/roles";

export function roleInferenceModel(player: SquadPlayer): RoleInferenceModel {
  return {
    display_role: player.display_role,
    role: player.role,
    career_role: player.career_role,
    club_history: [...player.stats, ...player.other_stats].map((row) => ({
      season: row.season,
      team_name: row.team_name,
      competition: row.competition,
      appearances: row.appearances,
      starts: row.starts,
      minutes: row.minutes,
    })),
    tactical_notes: player.tactical_notes,
    href: player.href,
  };
}

export function RoleInferenceContent({ model }: { model: RoleInferenceModel }) {
  const role = model.role;
  const career = model.career_role;
  const display = model.display_role;
  return (
    <div className="role-inference">
      <p>{display.reason}</p>
      <div className="grid two-col">
        <div>
          <p className="eyebrow">Current Aberdeen usage</p>
          {role.primary ? (
            <>
              <p>
                <strong>{role.primary}</strong> · {role.coverage} starts with a team-sheet
                role
              </p>
              {role.fm_label ? <p className="fine-print">Current positions: {role.fm_label}</p> : null}
              <table className="league-table compact">
<caption className="fine-print">Role inference: position, share and starts.</caption>
                <thead>
                  <tr>
                    <th>Role</th>
                    <th className="num">Role starts</th>
                    <th className="num">Mins</th>
                  </tr>
                </thead>
                <tbody>
                  {role.roles.map((row) => (
                    <tr key={`current-${row.code}`}>
                      <td>{row.label}</td>
                      <td className="num">{row.starts}</td>
                      <td className="num">{row.minutes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p>No starting-XI role observed for Aberdeen this season.</p>
          )}
        </div>
        <div>
          <p className="eyebrow">Career evidence</p>
          <p>
            <strong>{career.primary_slot?.role_label ?? career.dominant?.label ?? "Unknown"}</strong>
            {career.starts_with_role
              ? ` · ${Math.round((career.primary_slot?.share ?? 0) * 100)}% of ${career.starts_with_role} role starts`
              : ""}
          </p>
          <p className="fine-print">
            {career.fm_label || "No career positions"} ·{" "}
            {career.seasons_with_role} season{career.seasons_with_role === 1 ? "" : "s"} ·{" "}
            {career.starts_with_role}/{career.starts_total} checked starts have a role
          </p>
          {career.scopes.length ? (
            <p className="fine-print">
              {career.scopes
                .map((scope) => `${SCOPE_LABELS[scope.scope] ?? scope.scope} ${scope.starts}`)
                .join(" · ")}
            </p>
          ) : null}
          {career.slots.length ? (
            <table className="league-table compact">
<caption className="fine-print">Role inference: position, share and starts.</caption>
              <thead>
                <tr>
                  <th>Position</th>
                  <th>FM</th>
                  <th>Tier</th>
                  <th className="num">Role starts</th>
                </tr>
              </thead>
              <tbody>
                {career.slots.map((slot) => (
                  <tr key={`inference-${slot.slot}`}>
                    <td>{slot.label}</td>
                    <td>{slot.fm}</td>
                    <td>{slot.tier}</td>
                    <td className="num">{slot.starts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {career.slots.length ? <RoleMix shares={career.slots} /> : null}
        </div>
      </div>
      {!career.history.length ? (
        <div className="mini-block">
          <p className="eyebrow">Club history</p>
          {model.club_history.length ? (
            <div className="table-wrap">
              <table className="league-table compact">
<caption className="fine-print">Role inference: position, share and starts.</caption>
                <thead>
                  <tr>
                    <th>Season</th>
                    <th>Team</th>
                    <th>Competition</th>
                    <th className="num">Apps</th>
                    <th className="num">Starts</th>
                    <th className="num">Mins</th>
                  </tr>
                </thead>
                <tbody>
                  {model.club_history.map((row, index) => (
                    <tr key={`club-history-${index}`}>
                      <td>{row.season ?? "—"}</td>
                      <td>{row.team_name ?? "—"}</td>
                      <td>{row.competition ?? "—"}</td>
                      <td className="num">{row.appearances ?? "—"}</td>
                      <td className="num">{row.starts ?? "—"}</td>
                      <td className="num">{row.minutes ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>No club history is recorded in the licensed feed for this player.</p>
          )}
        </div>
      ) : null}
      {career.seasons.length ? (
        <details className="role-inference-heatmap">
          <summary>Career heat map</summary>
          <CareerRoleHeatmap career={career} />
        </details>
      ) : null}
      {model.tactical_notes.length ? (
        <div className="mini-block">
          <p className="eyebrow">Tactical context</p>
          {model.tactical_notes.map((note, index) => (
            <div key={`inference-note-${index}`}>
              <p>{note.note}</p>
              <p className="fine-print">
                {note.note_type.replaceAll("_", " ")} · source {note.source} · verified{" "}
                {note.verified_at}
              </p>
            </div>
          ))}
        </div>
      ) : null}
      <p className="fine-print">
        A role is a starting-XI observation. A substitute has no grid slot, and an
        intended position is only a note until it appears in the team sheet. The
        current Aberdeen role overrides the career label only when it is clearly
        different;{" "}
        {career.secondary_slots.length
          ? `secondary positions: ${career.secondary_slots.map((row) => row.fm).join(", ")}.`
          : "no secondary positions clear the threshold."}{" "}
        {career.stretch_slots.length
          ? `Stretch: ${career.stretch_slots.map((row) => row.fm).join(", ")}.`
          : ""}
      </p>
      <Link className="text-link" href={model.href}>
        Open the full player profile →
      </Link>
    </div>
  );
}

export function RoleInferenceDialog({
  player,
  onClose,
}: {
  player: SquadPlayer | null;
  onClose: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!player) return;
    const previous = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const focusableSelector =
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    closeRef.current?.focus();
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(focusableSelector)).filter(
        (element) => !element.hasAttribute("disabled"),
      );
      if (!focusable.length) {
        event.preventDefault();
        panel.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = "";
      previous?.focus();
    };
  }, [player, onClose]);

  if (!player) return null;
  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="dialog-panel"
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Position inference"
        tabIndex={-1}
      >
        <button
          className="dialog-close"
          ref={closeRef}
          type="button"
          onClick={onClose}
          aria-label="Close"
        >
          ×
        </button>
        <p className="eyebrow">Position inference</p>
        <h2>{player.display_role.label ?? player.role.primary ?? player.position ?? "Position unknown"}</h2>
        <RoleInferenceContent model={roleInferenceModel(player)} />
      </div>
    </div>
  );
}
