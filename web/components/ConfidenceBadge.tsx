const LABEL: Record<string, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
  unknown: "No confidence estimate",
};

const TITLE: Record<string, string> = {
  high: "Strong selection evidence for this pick",
  medium: "Moderate selection evidence for this pick",
  low: "Thin selection evidence for this pick",
  unknown: "No estimate: the lineup is incomplete or there is no selection evidence",
};

export function ConfidenceBadge({
  confidence,
  compact = false,
}: {
  confidence: string;
  compact?: boolean;
}) {
  const value = confidence || "unknown";
  return (
    <span
      className={`badge confidence-${value}`}
      title={TITLE[value] ?? "Confidence"}
      data-contract-indicator="confidence"
    >
      {compact ? (value === "unknown" ? "no estimate" : value) : (LABEL[value] ?? value)}
    </span>
  );
}
