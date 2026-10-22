export function BucketBars({
  title,
  buckets,
}: {
  title: string;
  buckets: Record<string, number>;
}) {
  const total = Object.values(buckets).reduce((sum, value) => sum + value, 0);
  const rows = Object.entries(buckets).sort((a, b) => b[1] - a[1]);
  return (
    <div className="mini-block">
      <p className="eyebrow">{title}</p>
      {rows.length ? (
        <div className="bar-list">
          {rows.map(([label, value]) => (
            <div className="bar-row" key={label}>
              <span className="bar-label">{label}</span>
              <span className="bar-track">
                <span
                  className="bar-fill"
                  style={{ width: `${total ? (value / total) * 100 : 0}%` }}
                />
              </span>
              <span className="bar-value">{Math.round((total ? value / total : 0) * 100)}%</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">No weight in this bucket yet.</p>
      )}
    </div>
  );
}
