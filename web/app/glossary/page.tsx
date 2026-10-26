import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { getDefinitions, type DefinitionEntry } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/glossary/" },
  title: "Glossary and definitions · fitba",
  description:
    "What every published metric and concept means: formula, unit, basis, coverage, source layer and the registered definitions behind the numbers.",
};

const CATEGORY_LABEL: Record<string, string> = {
  evidence: "Evidence",
  football: "Football",
  comparison: "Comparison",
  recruitment: "Recruitment",
  metric: "Registered metrics",
};

const CONCEPT_ORDER = ["evidence", "football", "comparison", "recruitment"];

function fragment(entry: DefinitionEntry): string {
  return entry.href.split("#", 2)[1] ?? entry.id;
}

function text(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  return typeof value === "string" ? value : String(value);
}

function DefinitionCard({
  entry,
  related,
}: {
  entry: DefinitionEntry;
  related: DefinitionEntry[];
}) {
  const formula = text(entry.formula);
  return (
    <article className="card definition-card" id={fragment(entry)}>
      <p className="eyebrow">{CATEGORY_LABEL[entry.category] ?? entry.category}</p>
      <h3>{entry.term}</h3>
      {entry.short ? <p>{entry.short}</p> : null}
      {entry.body && entry.body !== entry.short ? (
        <p className="fine-print">{entry.body}</p>
      ) : null}
      <dl className="definition-meta">
        {formula ? (
          <>
            <dt>Formula</dt>
            <dd>{formula}</dd>
          </>
        ) : null}
        {entry.unit ? (
          <>
            <dt>Unit</dt>
            <dd>{entry.unit}</dd>
          </>
        ) : null}
        {entry.basis ? (
          <>
            <dt>Basis</dt>
            <dd>{entry.basis}</dd>
          </>
        ) : null}
        {entry.coverage_tier ? (
          <>
            <dt>Coverage</dt>
            <dd>{entry.coverage_tier}</dd>
          </>
        ) : null}
        {entry.source_layer ? (
          <>
            <dt>Source layer</dt>
            <dd>{entry.source_layer}</dd>
          </>
        ) : null}
        {entry.metric_ids.length ? (
          <>
            <dt>Metric ids</dt>
            <dd>
              {entry.metric_ids.map((metricId, index) => (
                <span key={metricId}>
                  {index ? " · " : null}
                  <Link className="text-link" href={`/metrics/#metric-${metricId}`}>
                    {metricId}
                  </Link>
                </span>
              ))}
            </dd>
          </>
        ) : null}
      </dl>
      {entry.limitations.length ? (
        <p className="fine-print">
          Limits: {entry.limitations.join(" ")}
        </p>
      ) : null}
      {related.length ? (
        <p className="fine-print">
          Related:{" "}
          {related.map((item, index) => (
            <span key={item.id}>
              {index ? " · " : null}
              <Link className="text-link" href={item.href}>
                {item.term}
              </Link>
            </span>
          ))}
        </p>
      ) : null}
      <p className="fine-print">
        Registry version <code>{entry.registry_version}</code>.{" "}
        {entry.provenance === "registry"
          ? "Copied from the metric registry at publish time."
          : "Curated concept; it cannot override a registered formula, unit, basis or coverage tier."}
      </p>
    </article>
  );
}

export default function GlossaryPage() {
  const document = getDefinitions();
  if (!document) {
    return (
      <ContractPage surface="glossary" state="empty">
        <section className="page-head" data-contract="glossary.hero">
          <p className="eyebrow">Definitions</p>
          <h1>Glossary and definitions</h1>
          <p className="lede">No definitions document is published in this build.</p>
        </section>
      </ContractPage>
    );
  }

  const concepts = document.entries.filter((entry) => entry.provenance !== "registry");
  const metrics = document.entries.filter((entry) => entry.provenance === "registry");
  const byId = new Map(document.entries.map((entry) => [entry.id, entry]));
  const relatedFor = (entry: DefinitionEntry) =>
    (entry.related ?? [])
      .map((id) => byId.get(id))
      .filter((item): item is DefinitionEntry => Boolean(item));
  const conceptGroups: Array<{
    key: string;
    label: string;
    entries: DefinitionEntry[];
  }> = [];
  for (const category of [...CONCEPT_ORDER, "other"]) {
    const entries = concepts.filter((entry) =>
      category === "other"
        ? !CONCEPT_ORDER.includes(entry.category)
        : entry.category === category,
    );
    if (entries.length) {
      conceptGroups.push({
        key: category,
        label: CATEGORY_LABEL[category] ?? category,
        entries,
      });
    }
  }

  return (
    <ContractPage surface="glossary">
      <section className="page-head" data-contract="glossary.hero">
        <p className="eyebrow">Definitions</p>
        <h1>Glossary and definitions</h1>
        <p className="lede">
          What each published term and number means, with its formula, unit, basis,
          coverage and source layer. Metric entries are copied from the registry at
          publish time; curated concepts explain the vocabulary and cannot override a
          registered definition.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/metrics/">
            Metrics and audit
          </Link>
          <Link className="button button-ghost" href="/sources/">
            Sources
          </Link>
          <Link className="button button-ghost" href="/methodology/">
            Method
          </Link>
        </div>
        <p className="fine-print" data-contract-indicator="source">
          Registry version <code>{document.registry_version}</code>, reviewed{" "}
          {document.reviewed || "—"}. A definition never introduces a number that is
          not in the registry.
        </p>
      </section>

      <section className="section" data-contract="glossary.concepts">
        <div className="section-head">
          <div>
            <p className="eyebrow">Vocabulary</p>
            <h2>Concepts</h2>
          </div>
          <span className="badge badge-neutral">{concepts.length} curated</span>
        </div>
        <p>
          Concepts describe how a value is produced, compared or labelled. They may
          link to the metrics that use them; the metric entry remains the definition
          of the number.
        </p>
        {conceptGroups.map((group) => (
          <section className="definition-group" key={group.key}>
            <h3>{group.label}</h3>
            <div className="definition-grid">
              {group.entries.map((entry) => (
                <DefinitionCard
                  entry={entry}
                  related={relatedFor(entry)}
                  key={entry.id}
                />
              ))}
            </div>
          </section>
        ))}
      </section>

      <section className="section" data-contract="glossary.metrics">
        <div className="section-head">
          <div>
            <p className="eyebrow">The registry</p>
            <h2>Registered metrics</h2>
          </div>
          <span className="badge badge-neutral">{metrics.length} active</span>
        </div>
        <p>
          Every reader-facing number has one entry here. The formula, unit, basis,
          coverage tier and source layer are copied from{" "}
          <code>config/metrics.yaml</code>; verification and value history live on{" "}
          <Link className="text-link" href="/metrics/">
            Metrics and audit
          </Link>
          .
        </p>
        <div className="definition-grid">
          {metrics.map((entry) => (
            <DefinitionCard
              entry={entry}
              related={relatedFor(entry)}
              key={entry.id}
            />
          ))}
        </div>
      </section>

      <p className="back-link">
        <Link href="/metrics/">← Metrics and audit</Link>
        {" · "}
        <Link href="/sources/">Sources →</Link>
        {" · "}
        <Link href="/corrections/">Corrections →</Link>
      </p>
    </ContractPage>
  );
}
