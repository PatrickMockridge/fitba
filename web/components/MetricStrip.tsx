import type { ReactNode } from "react";
import { StatTile } from "@/components/StatTile";

export interface Metric {
  label: string;
  value: ReactNode;
  note?: string;
}

export function MetricStrip({
  items,
  columns,
}: {
  items: Metric[];
  columns?: 2 | 3 | 4 | 5;
}) {
  return (
    <div className={`metric-strip${columns ? ` cols-${columns}` : ""}`}>
      {items.map((item) => (
        <StatTile key={item.label} label={item.label} value={item.value} note={item.note} />
      ))}
    </div>
  );
}
