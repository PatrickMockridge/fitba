const LABEL: Record<string, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
  unknown: "Unknown confidence",
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
      title={LABEL[value] ?? "Confidence"}
    >
      {compact ? value : (LABEL[value] ?? value)}
    </span>
  );
}
