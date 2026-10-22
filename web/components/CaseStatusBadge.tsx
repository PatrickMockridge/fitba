export function CaseStatusBadge({ status }: { status: string }) {
  const label =
    status === "supported"
      ? "Supported"
      : status === "mixed"
        ? "Mixed"
        : status === "not_supported"
          ? "Not supported"
          : "Can't test yet";
  const className =
    status === "supported"
      ? "badge badge-ok"
      : status === "mixed"
        ? "badge badge-warn"
        : "badge badge-neutral";
  return <span className={className}>{label}</span>;
}
