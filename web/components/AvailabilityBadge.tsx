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

function evidenceTitle(
  reviewReason?: string | null,
  contradictedBy?: Record<string, unknown> | null,
  suspension?: Record<string, unknown> | null,
): string | null {
  const parts: string[] = [];
  if (reviewReason) parts.push(reviewReason.replaceAll("_", " "));
  if (contradictedBy) {
    const date = contradictedBy.date ? String(contradictedBy.date) : null;
    const squad = contradictedBy.squad_status
      ? String(contradictedBy.squad_status).replaceAll("_", " ")
      : null;
    const minutes = contradictedBy.minutes;
    if (date || squad || minutes !== undefined) {
      parts.push(
        [
          "Evidence:",
          squad,
          date,
          minutes !== undefined && minutes !== null ? `${minutes} min` : null,
        ]
          .filter(Boolean)
          .join(" "),
      );
    }
  }
  if (suspension && suspension.state === "served") {
    parts.push(
      `Suspension served${suspension.served_date ? ` on ${suspension.served_date}` : ""}`,
    );
  }
  return parts.length ? parts.join(" · ") : null;
}

export function AvailabilityBadge({
  status,
  note,
  compact = false,
  originalStatus,
  reviewRequired = false,
  reviewReason,
  reviewSeverity,
  contradictedBy,
  suspension,
}: {
  status?: string | null;
  note?: string | null;
  compact?: boolean;
  originalStatus?: string | null;
  reviewRequired?: boolean;
  reviewReason?: string | null;
  reviewSeverity?: string | null;
  contradictedBy?: Record<string, unknown> | null;
  suspension?: Record<string, unknown> | null;
}) {
  const value = status || "unknown";
  const reviewed = reviewRequired || Boolean(reviewSeverity);
  const recorded =
    originalStatus && originalStatus !== value
      ? ` (recorded ${LABELS[originalStatus] ?? originalStatus})`
      : "";
  const label =
    reviewed && value === "unknown"
      ? `Needs review${recorded}`
      : reviewed
        ? `${LABELS[value] ?? value} · review`
        : `${LABELS[value] ?? value}`;
  const title =
    evidenceTitle(reviewReason, contradictedBy, suspension) ??
    note ??
    "No verified team-news entry";
  return (
    <span
      className={`badge ${reviewed ? "badge-warn" : (CLASSES[value] ?? "badge-neutral")}`}
      title={title}
      data-contract-indicator="availability"
    >
      {compact ? label : `Availability: ${label}`}
    </span>
  );
}
