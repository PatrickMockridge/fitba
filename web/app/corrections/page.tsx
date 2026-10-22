import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { formatDate } from "@/lib/format";
import corrections from "@/data/corrections.json";

export const metadata = {
  alternates: { canonical: "/corrections/" },
  title: "Corrections · fitba",
  description:
    "The fitba corrections policy, contact route and dated correction log.",
};

export default function CorrectionsPage() {
  return (
    <ContractPage surface="corrections">
      <section className="page-head" data-contract="corrections.policy">
        <p className="eyebrow">Corrections</p>
        <h1>Corrections and contact</h1>
        <p className="lede">
          fitba is an independent public record, so it has to be correctable. If a
          page, label or number is wrong, report it with the page, the claim and a
          source. Corrections are recorded below with the date they were made.
        </p>
        <p className="fine-print" data-contract-indicator="source">
          Last reviewed {formatDate(corrections.last_reviewed)}. Report an error
          through the{" "}
          <a
            className="text-link"
            href={corrections.contact_url}
            target="_blank"
            rel="noreferrer"
            data-contract="corrections.contact"
          >
            public issue tracker
          </a>
          . Do not include personal information or unverified allegations.
        </p>
        <p className="fine-print">{corrections.note}</p>
      </section>

      <section className="card" data-contract="corrections.log">
        <div className="section-head">
          <div>
            <p className="eyebrow">Correction log</p>
            <h2>Dated corrections</h2>
          </div>
          <span className="badge badge-neutral">{corrections.entries.length} entries</span>
        </div>
        <div className="table-wrap">
          <table className="league-table">
            <caption className="fine-print">
              Dated corrections, the affected page and the replacement statement.
            </caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Page</th>
                <th scope="col">What was wrong</th>
                <th scope="col">Correction</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {corrections.entries.map((entry) => (
                <tr key={`${entry.date}-${entry.page}-${entry.claim}`}>
                  <td>{formatDate(entry.date)}</td>
                  <td>{entry.page}</td>
                  <td>{entry.claim}</td>
                  <td>{entry.correction}</td>
                  <td>
                    <span className="badge badge-ok">{entry.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print">
          The method and source rules are on{" "}
          <Link className="text-link" href="/methodology/">
            Methodology
          </Link>{" "}
          and{" "}
          <Link className="text-link" href="/sources/">
            Sources
          </Link>
          .
        </p>
      </section>
    </ContractPage>
  );
}
