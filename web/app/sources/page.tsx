import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import {
  formatDate,
  getManifest,
  getProvenance,
  type ProvenanceDocument,
} from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/sources/" }, title: "Sources and licences · fitba" };

function sourceName(data: ProvenanceDocument, sourceId: string) {
  if (sourceId === "computed") return "Computed on site";
  if (sourceId === "curated") return "Curated register";
  if (sourceId === "mixed") return "Mixed sources";
  if (sourceId === "derived") return "Derived on site";
  if (sourceId === "none") return "Not published";
  return (
    data.sources.find((source) => source.id === sourceId)?.name ??
    sourceId.replaceAll("_", " ")
  );
}

function primaryRows(data: ProvenanceDocument, layerId: string) {
  const layer = data.layers.find((item) => item.id === layerId);
  if (!layer) return "—";
  const rows = layer.sources
    .filter((source) => source.role === "primary")
    .reduce((total, source) => total + (source.rows ?? 0), 0);
  return rows ? rows.toLocaleString("en-GB") : "—";
}

export default function SourcesPage() {
  const data = getProvenance();
  const manifest = getManifest();
  if (!data) {
    return (
      <ContractPage surface="sources" state="empty">
        <section className="empty-state" data-contract="sources.empty">
          <h1>No provenance published</h1>
          <p>
            Run <code>uv run fitba publish</code> to build the layer truth table.
          </p>
        </section>
      </ContractPage>
    );
  }

  return (
    <ContractPage surface="sources">
      <section className="page-head" data-contract="sources.hero">
        <p className="eyebrow">Sources and licences</p>
        <h1>Where the data comes from</h1>
        <p className="lede">
          A layer-by-layer truth table: which source owns each number, what is a
          fallback, what is computed or curated, and where the licensed source
          does not cover the data. A source is never called primary for a layer
          it does not supply.
        </p>
        <p className="fine-print">
          Generated {formatDate(String(data.generated_at).slice(0, 10))} · season{" "}
          {data.season} · manifest{" "}
          {manifest?.dataset_version ?? "not published"}.
        </p>
      </section>

      <section className="card" data-contract="sources.layers">
        <div className="section-head">
          <div>
            <p className="eyebrow">Layer truth table</p>
            <h2>What owns each layer</h2>
          </div>
          <span className="badge badge-neutral">{data.layers.length} layers</span>
        </div>
        <div className="table-wrap">
          <table className="league-table compact">
<caption className="fine-print">Source layers and the source registry.</caption>
            <thead>
              <tr>
                <th>Layer</th>
                <th>Primary</th>
                <th>Fallback</th>
                <th>Status</th>
                <th className="num">Rows</th>
                <th>Scope</th>
              </tr>
            </thead>
            <tbody>
              {data.layers.map((layer) => (
                <tr key={layer.id}>
                  <td className="strong">{layer.label}</td>
                  <td>{sourceName(data, layer.primary)}</td>
                  <td>
                    {layer.fallback.length
                      ? layer.fallback.map((id) => sourceName(data, id)).join(", ")
                      : "—"}
                  </td>
                  <td>
                    <span
                      className={`badge ${
                        layer.status === "active"
                          ? "badge-ok"
                          : layer.status === "not_published"
                            ? "badge-neutral"
                            : "badge-warn"
                      }`}
                    >
                      {layer.status}
                    </span>
                  </td>
                  <td className="num">{primaryRows(data, layer.id)}</td>
                  <td className="fine-print">{layer.scope}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print">{data.notes}</p>
      </section>

      <section className="card" data-contract="sources.registry">
        <div className="section-head">
          <div>
            <p className="eyebrow">Active sources</p>
            <h2>Registry and attribution</h2>
          </div>
          <span className="badge badge-neutral">Rows = primary contributions</span>
        </div>
        <div className="table-wrap">
          <table className="league-table">
<caption className="fine-print">Source layers and the source registry.</caption>
            <thead>
              <tr>
                <th>Source</th>
                <th>Lane</th>
                <th>Primary layers</th>
                <th className="num">Rows</th>
                <th>Last checked</th>
              </tr>
            </thead>
            <tbody>
              {data.sources.map((source) => (
                <tr key={source.id}>
                  <td>
                    {source.url ? (
                      <a href={source.url} target="_blank" rel="noreferrer">
                        {source.name}
                      </a>
                    ) : (
                      source.name
                    )}
                  </td>
                  <td>
                    <code>{source.lane ?? "—"}</code>
                  </td>
                  <td className="fine-print">
                    {source.primary_layers.length
                      ? source.primary_layers.join(", ")
                      : "corroboration / gated"}
                  </td>
                  <td className="num">{source.rows.toLocaleString("en-GB")}</td>
                  <td>{source.last_verified || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print" data-contract-indicator="source">
          A row count belongs to the source only where it is the primary
          contributor. Curated transfer rows are not counted as API-Football
          rows; a gated source can appear with zero rows.
        </p>
      </section>

      <div className="grid two-col">
        <section className="card" data-contract="sources.migration">
          <div className="section-head">
            <div>
              <p className="eyebrow">Current-season league migration</p>
              <h2>Gate status</h2>
            </div>
            <span
              className={`badge ${
                data.migration.enabled ? "badge-ok" : "badge-warn"
              }`}
            >
              {data.migration.enabled ? "enabled" : "disabled"}
            </span>
          </div>
          <p>
            Active league-results source:{" "}
            <strong>{sourceName(data, data.migration.active_source)}</strong>.
          </p>
          <p className="fine-print">
            Gate: {data.migration.gate_status}. {data.migration.reason}
          </p>
          {data.migration.report ? (
            <p className="fine-print">
              Report: <code>{data.migration.report}</code>
            </p>
          ) : null}
          <p className="fine-print">
            The gate requires all four leagues, complete fixtures, exact scores
            for played matches and the team match stats the style layers need.
            A partial pass does not migrate.
          </p>
        </section>

        <section className="card" data-contract="sources.availability">
          <div className="section-head">
            <div>
              <p className="eyebrow">Availability</p>
              <h2>Team news is a special case</h2>
            </div>
            <span
              className={`badge ${
                data.availability.status === "available"
                  ? "badge-ok"
                  : "badge-warn"
              }`}
            >
              {data.availability.status}
            </span>
          </div>
          <p>
            Curated official AFC team news is the primary availability source.
            Provider injury snapshots are optional and labelled separately.
          </p>
          <p className="fine-print">
            Provider snapshot: {data.availability.provider_snapshot}.
            {data.availability.reason
              ? ` ${data.availability.reason.replaceAll("_", " ")}.`
              : ""}
          </p>
          <p className="fine-print" data-contract-indicator="unknown">
            A provider injury flag is not team news. Unknown stays unknown; no
            injury status is inferred from the provider boolean.
          </p>
        </section>
      </div>

      <section className="card" data-contract="sources.excluded">
        <div className="section-head">
          <div>
            <p className="eyebrow">Excluded</p>
            <h2>Sources we do not publish</h2>
          </div>
        </div>
        <ul className="plain-list">
          {data.excluded.map((item) => (
            <li key={item.id}>
              <strong>{item.id.replaceAll("_", " ")}</strong> — {item.reason}
            </li>
          ))}
        </ul>
      </section>

      <div className="grid two-col">
        <section className="card" data-contract="sources.derived">
          <p className="eyebrow">What is published</p>
          <h2>Derived, not raw</h2>
          <p>
            League tables, cup groups and rounds, aggregates, percentiles,
            curated fee bands and AFC headlines. Raw payloads and full event
            feeds stay in gitignored caches.
          </p>
          <p className="fine-print">
            Roles come from the licensed starting-XI grid. Preferred foot
            carries its source id, URL, revision and verification date; unknown
            is explicit. The rumour mill publishes curated links, an advisory
            profile and derived fan-signal aggregates. X is embedded, not
            ingested.
          </p>
        </section>
        <section className="card" data-contract="sources.no-raw">
          <p className="eyebrow">What is not</p>
          <h2>No raw redistribution</h2>
          <p>
            No full event feed, no source-shaped table, no raw market-value feed,
            no unlicensed tracking data and no betting odds. A source can be
            disabled and the site rebuilt from the remainder.
          </p>
        </section>
      </div>

      <p className="back-link">
        <Link href="/about/">← About fitba</Link> ·{" "}
        <Link href="/methodology/">Methodology</Link> ·{" "}
        <Link href="/analysis/">Data analysis</Link>
      </p>
    </ContractPage>
  );
}
