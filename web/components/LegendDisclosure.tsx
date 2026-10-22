import type { ReactNode } from "react";

export function LegendDisclosure({
  title = "How to read this page",
  children,
}: {
  title?: string;
  children: ReactNode;
}) {
  return (
    <details className="page-legend">
      <summary>{title}</summary>
      <div className="page-legend-body">{children}</div>
    </details>
  );
}
