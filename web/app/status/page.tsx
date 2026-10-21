import { getManifest } from "@/lib/data";

export const metadata = { title: "Data status · fitba" };

export default function StatusPage() {
  const manifest = getManifest();
  if (!manifest) {
    return (
      <section className="empty-state">
        <h1>No published data</h1>
        <p>Run <code>uv run fitba publish</code> to generate the dataset.</p>
      </section>
    );
  }
  const totalBytes = manifest.files.reduce((sum, file) => sum + file.bytes, 0);
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Data status</p>
        <h1>What is in this build</h1>
        <p className="lede">
          Dataset <code>{manifest.dataset_version}</code>, generated{" "}
          {new Date(manifest.generated_at).toLocaleString("en-GB", {
            timeZone: "UTC",
            dateStyle: "medium",
            timeStyle: "short",
          })}{" "}
          UTC. Season {manifest.season}.
        </p>
      </section>

      <div className="grid three-col">
        <div className="stat-tile">
          <span className="stat-label">Schema</span>
          <span className="stat-value">{manifest.schema_version}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Files</span>
          <span className="stat-value">{manifest.files.length}</span>
          <span className="stat-note">{(totalBytes / 1024).toFixed(1)} KB</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Profile</span>
          <span className="stat-value">{manifest.profile}</span>
        </div>
      </div>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>Competitions</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table className="league-table">
            <thead>
              <tr>
                <th>Competition</th>
                <th className="num">Matches</th>
                <th className="num">Expected</th>
                <th>Depth</th>
                <th className="num">Event matches</th>
                <th className="num">Player stats</th>
              </tr>
            </thead>
            <tbody>
              {manifest.coverage.competitions.map((row) => (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  <td className="num">{row.matches}</td>
                  <td className="num">{row.expected_matches}</td>
                  <td>{row.coverage}</td>
                  <td className="num">{row.events}</td>
                  <td className="num">{row.player_stats}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid two-col">
        <section className="card">
          <p className="eyebrow">Sources</p>
          <h2>Freshness</h2>
          <ul className="plain-list">
            {manifest.sources.map((source) => (
              <li key={source.id}>
                <strong>{source.name}</strong> · <code>{source.status}</code> ·{" "}
                {source.rows.toLocaleString("en-GB")} rows
                {source.last_verified ? ` · checked ${source.last_verified}` : ""}
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <p className="eyebrow">Marts</p>
          <h2>Published outputs</h2>
          <ul className="plain-list">
            {manifest.marts.map((mart) => (
              <li key={mart.id}>
                <code>{mart.id}</code> · {mart.rows} rows
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}
