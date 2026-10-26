import { CopyCitationButton } from "@/components/CopyCitationButton";

export function CitationBlock({
  title,
  datasetVersion,
  generatedAt,
  sources,
  metrics,
}: {
  title: string;
  datasetVersion: string;
  generatedAt: string;
  sources: string[];
  metrics: string[];
}) {
  return (
    <div className="citation-block" data-contract="page.citation">
      <div>
        <p className="eyebrow">Cite this page</p>
        <p className="fine-print" data-contract-indicator="source">
          {title}. Dataset <code>{datasetVersion}</code>, as of{" "}
          <code>{generatedAt}</code>.
          {sources.length ? ` Sources: ${sources.join("; ")}.` : " Source: published fitba record."}
          {metrics.length ? ` Definitions: ${metrics.join("; ")}.` : ""}
        </p>
      </div>
      <CopyCitationButton
        title={title}
        datasetVersion={datasetVersion}
        generatedAt={generatedAt}
        sources={sources}
        metrics={metrics}
      />
    </div>
  );
}
