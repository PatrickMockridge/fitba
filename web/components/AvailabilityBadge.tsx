const LABELS: Record<string, string> = {
  out: "Out",
  suspended: "Suspended",
  doubtful: "Doubtful",
  returned: "Returned",
  available: "Available",
  unknown: "Unknown",
  unavailable: "Unavailable",
  partial: "Partial",
  not_modelled: "Not modelled",
};

const CLASSES: Record<string, string> = {
  out: "badge-warn",
  suspended: "badge-warn",
  doubtful: "badge-warn",
  returned: "badge-ok",
  available: "badge-ok",
  unknown: "badge-neutral",
};

export function AvailabilityBadge({
  status,
  note,
  compact = false,
}: {
  status?: string | null;
  note?: string | null;
  compact?: boolean;
}) {
  const value = status || "unknown";
  return (
    <span
      className={`badge ${CLASSES[value] ?? "badge-neutral"}`}
      title={note ?? "No verified team-news entry"}
      data-contract-indicator="availability"
    >
      {compact ? LABELS[value] ?? value : `Availability: ${LABELS[value] ?? value}`}
    </span>
  );
}
