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

      {manifest.coverage.cups?.length ? (
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Cups</p>
              <h2>Licensed coverage</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table className="league-table">
              <thead>
                <tr>
                  <th>Competition</th>
                  <th className="num">Licensed</th>
                  <th className="num">Official</th>
                  <th>Coverage</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {manifest.coverage.cups.map((cup) => (
                  <tr key={cup.id}>
                    <td>{cup.name}</td>
                    <td className="num">{cup.ties ?? cup.matches ?? "—"}</td>
                    <td className="num">{cup.official_ties ?? "—"}</td>
                    <td>
                      <span
                        className={
                          cup.coverage === "partial" ? "badge badge-warn" : "badge badge-ok"
                        }
                      >
                        {cup.coverage}
                      </span>
                    </td>
                    <td className="fine-print">{cup.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {manifest.coverage.transfers ? (
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Transfers</p>
              <h2>Confirmed business</h2>
            </div>
            <span className="badge badge-warn">Curated</span>
          </div>
          <p>
            {manifest.coverage.transfers.count} rows ·{" "}
            {manifest.coverage.transfers.confirmed} official-confirmed ·{" "}
            {manifest.coverage.transfers.curated} source-linked curated.
          </p>
          <p className="fine-print">{manifest.coverage.transfers.note}</p>
        </section>
      ) : null}

      {manifest.coverage.history ? (
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">History</p>
              <h2>The Cormack era</h2>
            </div>
            <span className="badge badge-neutral">
              {manifest.coverage.history.completed} completed + current
            </span>
          </div>
          <p>
            {manifest.coverage.history.seasons} curated seasons ·{" "}
            {manifest.coverage.history.staff} people ·{" "}
            {manifest.coverage.history.honours} major honours.
          </p>
          <p className="fine-print">{manifest.coverage.history.note}</p>
        </section>
      ) : null}

      {manifest.coverage.rumours || manifest.coverage.forum ? (
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Rumours and fan signal</p>
              <h2>Curated and sampled</h2>
            </div>
            <span className="badge badge-warn">Separate from confirmed business</span>
          </div>
          {manifest.coverage.rumours ? (
            <p>
              {manifest.coverage.rumours.count} curated rumour rows ·{" "}
              {manifest.coverage.rumours.active} active.
            </p>
          ) : null}
          {manifest.coverage.forum ? (
            <p>
              {manifest.coverage.forum.topics} forum topics and{" "}
              {manifest.coverage.forum.posts} first-page posts sampled ·{" "}
              {manifest.coverage.forum.raw_posts_published
                ? "raw posts published"
                : "no raw posts published"}
              .
            </p>
          ) : null}
          <p className="fine-print">
            {manifest.coverage.rumours?.note} {manifest.coverage.forum?.note}
          </p>
        </section>
      ) : null}

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
