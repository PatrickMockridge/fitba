"use client";

import { useMemo, useState } from "react";
import { TransferCard } from "@/components/TransferCard";
import type { TransferWindow, TransfersFile } from "@/lib/data";

type Direction = "all" | "in" | "out";
type Kind = "all" | "permanent" | "loan" | "free";
type Range = "recent" | "further" | "out_of_window";

const RANGE_LABEL: Record<Range, string> = {
  recent: "Recent",
  further: "Further back",
  out_of_window: "Out of window",
};

interface SummaryTotals {
  arrivals: number;
  departures: number;
  net_low: number | null;
  net_high: number | null;
  known_count: number;
  modelled_count: number;
  loan_count: number;
  loans_in: number;
  loans_out: number;
  confidence: string;
  windows: number;
}

function money(value: number) {
  const sign = value < 0 ? "−" : "+";
  return `${sign}£${Math.abs(value).toLocaleString("en-GB")}`;
}

const CONFIDENCE_RANK: Record<string, number> = {
  unknown: 0,
  low: 1,
  medium: 2,
  high: 3,
};

function totals(windows: TransferWindow[]): SummaryTotals {
  return windows.reduce<SummaryTotals>(
    (acc, window) => {
      const counts = window.valuation_counts ?? {};
      return {
        arrivals: acc.arrivals + window.arrivals,
        departures: acc.departures + window.departures,
        net_low:
          window.inferred_net_low_gbp === null ||
          window.inferred_net_low_gbp === undefined
            ? acc.net_low
            : (acc.net_low ?? 0) + window.inferred_net_low_gbp,
        net_high:
          window.inferred_net_high_gbp === null ||
          window.inferred_net_high_gbp === undefined
            ? acc.net_high
            : (acc.net_high ?? 0) + window.inferred_net_high_gbp,
        known_count:
          acc.known_count +
          Number(counts.disclosed ?? 0) +
          Number(counts.reported ?? 0),
        modelled_count: acc.modelled_count + Number(counts.modelled ?? 0),
        loan_count: acc.loan_count + Number(counts.loan ?? 0),
        loans_in: acc.loans_in + window.loans_in,
        loans_out: acc.loans_out + window.loans_out,
        confidence:
          (CONFIDENCE_RANK[window.valuation_confidence ?? "unknown"] ?? 0) <
          (CONFIDENCE_RANK[acc.confidence] ?? 0)
            ? (window.valuation_confidence ?? "unknown")
            : acc.confidence,
        windows: acc.windows + 1,
      };
    },
    {
      arrivals: 0,
      departures: 0,
      net_low: null,
      net_high: null,
      known_count: 0,
      modelled_count: 0,
      loan_count: 0,
      loans_in: 0,
      loans_out: 0,
      confidence: "high",
      windows: 0,
    },
  );
}

function Summary({ value }: { value: SummaryTotals }) {
  const netLabel =
    value.net_low === null || value.net_high === null
      ? "Not modelled"
      : `${money(value.net_low)} – ${money(value.net_high)}`;
  return (
    <div className="stat-row four">
      <div className="stat-tile">
        <span className="stat-label">Arrivals</span>
        <span className="stat-value">{value.arrivals}</span>
        <span className="stat-note">
          {value.windows === 1 ? "this window" : `across ${value.windows} windows`}
        </span>
      </div>
      <div className="stat-tile">
        <span className="stat-label">Departures</span>
        <span className="stat-value">{value.departures}</span>
        <span className="stat-note">permanent, loan, free</span>
      </div>
      <div className="stat-tile">
        <span className="stat-label">Estimated net</span>
        <span className="stat-value">{netLabel}</span>
        <span className="stat-note">
          inferred · {value.windows ? value.confidence : "unknown"} confidence ·{" "}
          {value.known_count} known · {value.modelled_count} modelled ·{" "}
          {value.loan_count} loans
        </span>
      </div>
      <div className="stat-tile">
        <span className="stat-label">Loans out</span>
        <span className="stat-value">{value.loans_out}</span>
        <span className="stat-note">
          {value.loans_in} in · loan fees excluded from net
        </span>
      </div>
    </div>
  );
}

export function TransferBoard({ data }: { data: TransfersFile }) {
  const groups = data.window_groups ?? {
    recent: data.windows.map((window) => window.key),
    further: [],
    out_of_window: [],
    upcoming: [],
  };
  const [range, setRange] = useState<Range>("recent");
  const [windowKey, setWindowKey] = useState("all");
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
  const outOfWindowCount = data.transfers.filter((transfer) =>
    groups.out_of_window.includes(`${transfer.season}-${transfer.window}`),
  ).length;

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
              onClick={() => changeRange(value)}
            >
              {RANGE_LABEL[value]}
            </button>
          ))}
        </div>

        <label>
          Window
          <select
            value={windowKey}
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
              onClick={() => setKind(value)}
            >
              {value === "all" ? "All types" : value}
            </button>
          ))}
        </div>
      </div>

      <Summary value={totals(activeWindows)} />

      <p className="fine-print">
        Estimated net is a range built from disclosed/reported fee anchors and a
        transparent age, position and market model. It is not an audited balance;
        negative means income exceeds spend. Free transfers count as zero fee;
        loan fees are excluded.{" "}
        <a className="text-link" href="/methodology/">
          How the range is built →
        </a>
      </p>

      <p className="fine-print">
        {selected ? selected.label : allLabel} · {filtered.length} deal
        {filtered.length === 1 ? "" : "s"} in this view.{" "}
        <span
          className={`badge ${
            (selected?.coverage ?? groupWindows[0]?.coverage) === "audited"
              ? "badge-ok"
              : "badge-warn"
          }`}
        >
          {(selected?.coverage ?? groupWindows[0]?.coverage) === "audited"
            ? "Audited windows"
            : "Curated partial"}
        </span>
        {selected?.era_context === "pre_era"
          ? " Summer 2019 predates Cormack's chairmanship."
          : ""}
        {range === "recent" && outOfWindowCount > 0
          ? ` ${outOfWindowCount} out-of-window move${
              outOfWindowCount === 1 ? "" : "s"
            } available under Out of window.`
          : ""}
        {range === "further"
          ? " Earlier windows are curated partial, not audited against a seniority review."
          : ""}
      </p>

      <div className="transfer-grid">
        {filtered.map((transfer) => (
          <TransferCard key={transfer.transfer_id} transfer={transfer} />
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="muted">No confirmed business matches these filters.</p>
      ) : null}
    </section>
  );
}
