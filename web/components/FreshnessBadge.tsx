import { dataAgeHours, type Manifest } from "@/lib/data";

export function FreshnessBadge({ manifest }: { manifest: Manifest | null }) {
  if (!manifest) {
    return (
      <span className="badge badge-warn" data-contract-indicator="freshness">
        No published data
      </span>
    );
  }
  const age = dataAgeHours(manifest);
  if (age === null) {
    return (
      <span className="badge badge-warn" data-contract-indicator="freshness">
        Unknown freshness
      </span>
    );
  }
  const stale = age > 48;
  const label =
    age < 1
      ? "updated this hour"
      : age < 48
        ? `updated ${Math.round(age)}h ago`
        : `updated ${Math.round(age / 24)}d ago`;
  return (
    <span
      className={stale ? "badge badge-warn" : "badge badge-ok"}
      data-contract-indicator="freshness"
    >
      {stale ? "stale · " : ""}
      {label}
    </span>
  );
}
