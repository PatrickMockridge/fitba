"use client";

import { useMemo, useState } from "react";
import { PlayerLink } from "@/components/PlayerLink";
import { TableFrame, Th } from "@/components/TableFrame";
import { formatDate } from "@/lib/format";
import type { TransferRecord, TransferWindow, TransfersFile } from "@/lib/data";

type Direction = "all" | "in" | "out";
type Kind = "all" | "permanent" | "loan" | "free";
type Range = "recent" | "further" | "out_of_window";

const RANGE_LABEL: Record<Range, string> = {
  recent: "Recent",
  further: "Further back",
  out_of_window: "Out of window",
};

const KIND_LABEL: Record<string, string> = {
  permanent: "Permanent",
  loan: "Loan",
  free: "Free",
};

function sourceLabel(record: TransferRecord) {
  const urls = (record.source_urls ?? []).join(" ").toLowerCase();
  if (urls.includes("afc.co.uk")) return "AFC";
  if (urls.includes("wikipedia.org")) return "Wikipedia";
  return "Feed";
}

export function TransferBoard({ data }: { data: TransfersFile }) {
  const groups = data.window_groups ?? {
    recent: data.windows.map((window) => window.key),
    further: [],
    out_of_window: [],
    upcoming: [],
  };
  const fallbackWindow =
    groups.recent?.[0] ??
    data.windows.find((window) => window.state !== "upcoming")?.key ??
    "all";
  const [range, setRange] = useState<Range>("recent");
  const [windowKey, setWindowKey] = useState(fallbackWindow);
  const [direction, setDirection] = useState<Direction>("all");
  const [kind, setKind] = useState<Kind>("all");

  const groupKeys = groups[range] ?? [];
  const groupWindows = groupKeys
    .map((key) => data.windows.find((window) => window.key === key))
    .filter((window): window is TransferWindow => Boolean(window));
  const selected = data.windows.find((window) => window.key === windowKey);
  const activeWindows = selected ? [selected] : groupWindows;

  const filtered = useMemo(() => {
    const keys = new Set(activeWindows.map((window) => window.key));
    return data.transfers.filter((transfer) => {
      if (!keys.has(`${transfer.season}-${transfer.window}`)) return false;
      if (direction !== "all" && transfer.direction !== direction) return false;
      if (kind === "permanent" && transfer.transfer_kind !== "permanent") return false;
      if (kind === "loan" && transfer.transfer_kind !== "loan") return false;
      if (kind === "free" && transfer.transfer_kind !== "free") return false;
      return true;
    });
  }, [activeWindows, data.transfers, direction, kind]);

  const allLabel =
    range === "recent"
      ? "All recent"
      : range === "further"
        ? "All further back"
        : "All out of window";
  const viewLabel = selected ? selected.label : allLabel;

  function changeRange(next: Range) {
    setRange(next);
    setWindowKey("all");
  }

  return (
    <section>
      <div className="board-controls">
        <div className="board-toggle" role="group" aria-label="Window range">
          {(["recent", "further", "out_of_window"] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={range === value ? "is-active" : undefined}
              aria-pressed={range === value}
              onClick={() => changeRange(value)}
            >
              {RANGE_LABEL[value]}
            </button>
          ))}
        </div>

        <label>
          Window
          <select
            value={selected ? windowKey : "all"}
            onChange={(event) => setWindowKey(event.target.value)}
          >
            <option value="all">{allLabel}</option>
            {groupWindows.map((window) => (
              <option key={window.key} value={window.key}>
                {window.label}
                {window.coverage === "curated_partial" ? " · curated" : ""}
              </option>
            ))}
          </select>
        </label>

        <div className="board-toggle" role="group" aria-label="Direction">
          {(["all", "in", "out"] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={direction === value ? "is-active" : undefined}
              aria-pressed={direction === value}
              onClick={() => setDirection(value)}
            >
              {value === "all" ? "All" : value === "in" ? "In" : "Out"}
            </button>
          ))}
        </div>

        <div className="board-toggle" role="group" aria-label="Deal type">
          {(["all", "permanent", "loan", "free"] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={kind === value ? "is-active" : undefined}
              aria-pressed={kind === value}
              onClick={() => setKind(value)}
            >
              {value === "all" ? "All types" : KIND_LABEL[value] ?? value}
            </button>
          ))}
        </div>
      </div>

      <p className="muted" aria-live="polite">
        {viewLabel} · {filtered.length} move{filtered.length === 1 ? "" : "s"}
      </p>

      {filtered.length ? (
        <TableFrame
          label={`${viewLabel} transfer register`}
          caption={`${viewLabel} Aberdeen transfers`}
          className="league-table compact register-table stack-mobile"
        >
          <thead>
            <tr>
              <Th>Date</Th>
              <Th>Player</Th>
              <Th>In/Out</Th>
              <Th>Type</Th>
              <Th>From</Th>
              <Th>To</Th>
              <Th>Fee</Th>
              <Th>Source</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((transfer) => (
              <tr key={transfer.transfer_id}>
                <td data-label="Date">{formatDate(transfer.date_effective)}</td>
                <td data-label="Player">
                  <PlayerLink name={transfer.player_name} href={transfer.player_href} />
                </td>
                <td data-label="In/Out">{transfer.direction === "in" ? "In" : "Out"}</td>
                <td data-label="Type">
                  {KIND_LABEL[transfer.transfer_kind] ?? transfer.transfer_kind}
                </td>
                <td data-label="From">{transfer.from_club_name}</td>
                <td data-label="To">{transfer.to_club_name}</td>
                <td data-label="Fee">{transfer.fee_display}</td>
                <td data-label="Source">{sourceLabel(transfer)}</td>
              </tr>
            ))}
          </tbody>
        </TableFrame>
      ) : (
        <p className="muted">No moves match these filters.</p>
      )}
    </section>
  );
}
