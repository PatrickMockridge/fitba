import { formatDate } from "@/lib/format";

export function AsOfBadge({
  generatedAt,
  datasetState,
  staleReason,
  label = "Data as of",
}: {
  generatedAt: string | null | undefined;
  datasetState?: string | null;
  staleReason?: string | null;
  label?: string;
}) {
  if (!generatedAt) {
    return (
      <span className="badge badge-warn" data-contract-indicator="freshness">
        {label} unknown
      </span>
    );
  }
  const state = datasetState ?? "fresh";
  const stale = state === "stale" || state === "partial" || state === "unavailable";
  return (
    <span
      className={stale ? "badge badge-warn" : "badge badge-neutral"}
      data-contract-indicator="freshness"
      title={staleReason ?? undefined}
    >
      {label} {formatDate(generatedAt)}
      {state !== "fresh" ? ` · ${state}` : ""}
    </span>
  );
}
