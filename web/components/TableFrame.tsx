import type { ReactNode } from "react";

export function TableFrame({
  children,
  label,
  sticky = true,
}: {
  children: ReactNode;
  label: string;
  sticky?: boolean;
}) {
  return (
    <div
      className="table-wrap"
      data-sticky={sticky ? "true" : undefined}
      role="region"
      aria-label={label}
      tabIndex={0}
    >
      {children}
    </div>
  );
}
