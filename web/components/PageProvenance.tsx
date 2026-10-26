import Link from "next/link";
import { AsOfBadge } from "@/components/AsOfBadge";
import { CitationBlock } from "@/components/CitationBlock";
import { getManifest, getPageMeta, getPageMetaForSurface, getProvenance } from "@/lib/data";

const METRIC_LIMIT = 18;

export function PageProvenance({ surface }: { surface: string }) {
  const meta = getPageMetaForSurface(surface);
  const pageMeta = getPageMeta();
  const manifest = getManifest();
  const provenance = getProvenance();
  if (!meta || !manifest || !pageMeta) return null;

  const layerIndex = new Map((provenance?.layers ?? []).map((layer) => [layer.id, layer]));
  const layers = meta.layers
    .map((id) => layerIndex.get(id))
    .filter((layer): layer is NonNullable<typeof layer> => Boolean(layer));
  const sourceNames = Array.from(
    new Set(
      layers.flatMap((layer) => [layer.primary, ...(layer.fallback ?? [])]),
    ),
  ).filter(Boolean) as string[];
  const sourceLabels = sourceNames.map((id) => {
    const source = (provenance?.sources ?? []).find((item) => item.id === id);
    return source?.name ?? id;
  });
  const metricIds = meta.metrics;
  const shownMetrics = metricIds.slice(0, METRIC_LIMIT);

  return (
    <section className="card page-provenance" data-contract="page.provenance">
      <div className="section-head">
        <div>
          <p className="eyebrow">Provenance</p>
          <h2>How this page is sourced</h2>
        </div>
        <AsOfBadge
          generatedAt={pageMeta.generated_at}
          datasetState={manifest.dataset_state}
        />
      </div>
      <p className="fine-print">
        Dataset <code>{manifest.dataset_version}</code>. Sources and coverage are
        listed below; the page keeps its own source and uncertainty labels.
      </p>
      {layers.length ? (
        <ul className="plain-list">
          {layers.map((layer) => (
            <li key={layer.id}>
              <Link className="text-link" href="/sources/">
                {layer.label}
              </Link>
              <span className="muted">
                {" "}
                · {layer.primary}
                {layer.fallback?.length ? `; fallback ${layer.fallback.join(", ")}` : ""}
                {layer.status ? ` · ${layer.status}` : ""}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="fine-print">
          {meta.no_layers_reason ?? "No data layer is directly mapped to this page."}
        </p>
      )}
      {metricIds.length ? (
        <p className="fine-print">
          Definitions:{" "}
          {shownMetrics.map((metricId, index) => (
            <span key={metricId}>
              {index ? " · " : null}
              <Link className="text-link" href={`/metrics/#metric-${metricId}`}>
                {metricId}
              </Link>
            </span>
          ))}
          {metricIds.length > shownMetrics.length
            ? ` · ${metricIds.length - shownMetrics.length} more in the metric registry`
            : null}
        </p>
      ) : null}
      <p className="fine-print">
        Corrections and changes are recorded on{" "}
        <Link className="text-link" href="/corrections/">
          Corrections and contact
        </Link>
        .
      </p>
      <CitationBlock
        title={meta.label}
        datasetVersion={manifest.dataset_version}
        generatedAt={pageMeta.generated_at}
        sources={sourceLabels}
        metrics={shownMetrics}
      />
    </section>
  );
}
