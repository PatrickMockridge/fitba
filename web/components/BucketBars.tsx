export function BucketBars({
  title,
  buckets,
  absolute = false,
}: {
  title: string;
  buckets: Record<string, number>;
  absolute?: boolean;
}) {
  const total = Object.values(buckets).reduce((sum, value) => sum + value, 0);
  const max = Math.max(1, ...Object.values(buckets));
  const rows = Object.entries(buckets).sort((a, b) => b[1] - a[1]);
  return (
    <div className="mini-block">
      <p className="eyebrow">{title}</p>
      {rows.length ? (
        <div className="bar-list">
          {rows.map(([label, value]) => {
            const share = total ? value / total : 0;
            const width = absolute ? (value / max) * 100 : share * 100;
            return (
              <div className="bar-row" key={label}>
                <span className="bar-label">{label}</span>
                <span className="bar-track">
                  <span className="bar-fill" style={{ width: `${width}%` }} />
                </span>
                <span className="bar-value">
                  {absolute ? `${value} · ${Math.round(share * 100)}%` : `${Math.round(share * 100)}%`}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="muted">No weight in this bucket yet.</p>
      )}
    </div>
  );
}
