"use client";

import { useMemo, useState } from "react";
import { RumourCard } from "@/components/RumourCard";
import type { RumoursFile, RumourStatus } from "@/lib/data";

type StatusFilter = "all" | RumourStatus;
type ConfidenceFilter = "all" | "high" | "medium" | "low";
type SourceFilter = "all" | "press" | "journalist" | "forum" | "club";
type DirectionFilter = "all" | "in" | "out";
type AffiliationFilter =
  | "all"
  | "external_target"
  | "former_player"
  | "current_squad"
  | "loan_out"
  | "current_non_official"
  | "unknown";

export function RumourBoard({ data }: { data: RumoursFile }) {
  const [status, setStatus] = useState<StatusFilter>("all");
  const [confidence, setConfidence] = useState<ConfidenceFilter>("all");
  const [source, setSource] = useState<SourceFilter>("all");
  const [direction, setDirection] = useState<DirectionFilter>("all");
  const [affiliation, setAffiliation] = useState<AffiliationFilter>("all");

  const filtered = useMemo(
    () =>
      data.rumours.filter((rumour) => {
        if (status !== "all" && rumour.status !== status) return false;
        if (confidence !== "all" && rumour.confidence !== confidence) return false;
        if (source !== "all" && !rumour.source_types.includes(source)) return false;
        if (direction !== "all" && rumour.direction !== direction) return false;
        if (affiliation !== "all" && (rumour.affiliation ?? "unknown") !== affiliation) {
          return false;
        }
        return true;
      }),
    [data.rumours, status, confidence, source, direction, affiliation],
  );

  if (data.rumours.length === 0) {
    return (
      <div className="empty-state compact">
        <h3>No curated rumours yet</h3>
        <p>
          The register is deliberately empty until a link has a public source, a
          status and an editorial confidence. Fan chatter is shown below as a
          signal, not as a rumour.
        </p>
      </div>
    );
  }

  return (
    <section>
      <div className="board-controls">
        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}>
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="confirmed">Confirmed</option>
            <option value="denied">Denied</option>
            <option value="stale">Stale</option>
          </select>
        </label>

        <label>
          Confidence
          <select
            value={confidence}
            onChange={(event) => setConfidence(event.target.value as ConfidenceFilter)}
          >
            <option value="all">All confidence</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>

        <label>
          Source type
          <select value={source} onChange={(event) => setSource(event.target.value as SourceFilter)}>
            <option value="all">All sources</option>
            <option value="press">Press</option>
            <option value="journalist">Journalist</option>
            <option value="forum">Forum</option>
            <option value="club">Club</option>
          </select>
        </label>

        <label>
          Affiliation
          <select
            value={affiliation}
            onChange={(event) => setAffiliation(event.target.value as AffiliationFilter)}
          >
            <option value="all">All affiliations</option>
            <option value="external_target">External target</option>
            <option value="former_player">Former player</option>
            <option value="current_squad">Current squad</option>
            <option value="loan_out">On loan out</option>
            <option value="current_non_official">At Aberdeen (not official)</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>

        <div className="board-toggle" role="group" aria-label="Direction">
          {(["all", "in", "out"] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={direction === value ? "is-active" : undefined}
              onClick={() => setDirection(value)}
            >
              {value === "all" ? "All" : value === "in" ? "In" : "Out"}
            </button>
          ))}
        </div>
      </div>

      <p className="fine-print">
        {filtered.length} link{filtered.length === 1 ? "" : "s"} in this view.{" "}
        {data.summary.by_status.active ?? 0} active in the register.
      </p>

      <div className="rumour-grid">
        {filtered.map((rumour) => (
          <RumourCard key={rumour.rumour_id} rumour={rumour} />
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="muted">No curated rumours match these filters.</p>
      ) : null}

      {/* TODO(engagement): shared votes, polls and submissions are deliberately
          not built here. See config/engagement.yaml and docs/rumours.md. */}
    </section>
  );
}
