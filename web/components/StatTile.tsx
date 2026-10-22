export function StatTile({
  label,
  value,
  note,
  indicator,
}: {
  label: string;
  value: React.ReactNode;
  note?: string;
  indicator?: "unknown" | "confidence" | "availability";
}) {
  return (
    <div className="stat-tile" data-contract-indicator={indicator}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {note ? <span className="stat-note">{note}</span> : null}
    </div>
  );
}
