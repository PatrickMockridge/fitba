import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { TableFrame } from "@/components/TableFrame";
import { getChangelog } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const metadata = {
  alternates: { canonical: "/corrections/" },
  title: "Corrections and changes · fitba",
  description:
    "The fitba corrections policy, contact route, dated corrections and metric changes.",
};

const KIND_LABEL: Record<string, string> = {
  correction: "Correction",
  metric: "Metric change",
  source: "Source",
  page: "Page",
  data: "Data",
};

export default function CorrectionsPage() {
  const changelog = getChangelog();
  if (!changelog) {
    return (
      <ContractPage surface="corrections" state="empty">
        <section className="page-head" data-contract="corrections.policy">
          <p className="eyebrow">Corrections</p>
          <h1>Corrections and contact</h1>
          <p className="lede">No correction log is published in this build.</p>
        </section>
      </ContractPage>
    );
  }
  const corrections = changelog.entries.filter((entry) => entry.kind === "correction");
  const metrics = changelog.entries.filter((entry) => entry.kind === "metric");
  return (
    <ContractPage surface="corrections">
      <section className="page-head" data-contract="corrections.policy">
        <p className="eyebrow">Corrections</p>
        <h1>Corrections and contact</h1>
        <p className="lede">
          fitba is an independent public record, so it has to be correctable. A
          correction changes a factual value against a public source. A disagreement
          with fitba&apos;s reading is not a correction and does not enter the log.
        </p>
        <p className="fine-print" data-contract-indicator="source">
          Last reviewed {formatDate(changelog.last_reviewed)}. Report an error through
          the{" "}
          <a
            className="text-link"
            href={changelog.contact_url}
            rel="noreferrer"
            data-contract="corrections.contact"
          >
            contact route
          </a>
          . Do not include personal information or unverified allegations.
        </p>
        <p className="fine-print">{changelog.note}</p>
      </section>

      <section className="card" data-contract="corrections.log">
        <div className="section-head">
          <div>
            <p className="eyebrow">Public log</p>
            <h2>Corrections and changes</h2>
          </div>
          <span className="badge badge-neutral">{changelog.entries.length} entries</span>
        </div>
        <p className="fine-print">
          {corrections.length} factual corrections · {metrics.length} metric changes.
          The log is append-only. Metric changes keep their full definition and
          verification narrative in{" "}
          <Link className="text-link" href="/metrics/">
            Metrics and audit
          </Link>
          .
        </p>
        <p className="fine-print">
          On a narrow screen the table scrolls sideways; every column stays
          available.
        </p>
        <TableFrame label="Corrections and changes">
          <table className="league-table corrections-table">
            <caption className="fine-print">
              Dated corrections and changes, the affected page and the replacement
              statement.
            </caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Kind</th>
                <th scope="col">Page</th>
                <th scope="col">What changed</th>
                <th scope="col">Detail</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {changelog.entries.map((entry) => (
                <tr key={entry.id} id={`entry-${entry.id}`}>
                  <td>{formatDate(entry.date)}</td>
                  <td>{KIND_LABEL[entry.kind] ?? entry.kind}</td>
                  <td>
                    {entry.pages.length
                      ? entry.pages.map((page, index) => (
                          <span key={`${entry.id}-${page}`}>
                            {index ? ", " : null}
                            <Link className="text-link" href={page}>
                              {page}
                            </Link>
                          </span>
                        ))
                      : "—"}
                  </td>
                  <td>
                    <strong>{entry.title}</strong>
                    <span className="muted"> · {entry.summary}</span>
                  </td>
                  <td>
                    {entry.evidence.length
                      ? entry.evidence.map((item, index) => (
                          <span key={`${entry.id}-${item.url}`}>
                            {index ? " · " : null}
                            <Link className="text-link" href={item.url}>
                              {item.label}
                            </Link>
                          </span>
                        ))
                      : "—"}
                  </td>
                  <td>
                    <span className="badge badge-ok">{entry.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableFrame>
        <p className="fine-print">
          The method and source rules are on{" "}
          <Link className="text-link" href="/methodology/">
            Methodology
          </Link>{" "}
          and{" "}
          <Link className="text-link" href="/sources/">
            Sources
          </Link>{" "}
          and{" "}
          <Link className="text-link" href="/claims/">
            Claims and evidence
          </Link>
          .
        </p>
      </section>
    </ContractPage>
  );
}
