import type { ReactNode, ThHTMLAttributes } from "react";

export function TableFrame({
  label,
  caption,
  className = "league-table compact register-table",
  children,
}: {
  label: string;
  caption: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className="table-wrap"
      role="region"
      aria-label={label}
      tabIndex={0}
    >
      <table className={className}>
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function Th({
  className,
  children,
  ...props
}: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th scope="col" className={className} {...props}>
      {children}
    </th>
  );
}
