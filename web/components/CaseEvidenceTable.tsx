import { CaseStatusBadge } from "@/components/CaseStatusBadge";
import { TableFrame } from "@/components/TableFrame";
import type { CaseEvidence } from "@/lib/data";

export function CaseEvidenceTable({ evidence }: { evidence: CaseEvidence[] }) {
  return (
    <TableFrame label="Claim evidence" sticky={false}>
      <table className="league-table case-evidence" data-contract="case.claim.evidence">
        <caption className="fine-print">
          Claim evidence with count, sample, period, status and source.
        </caption>
        <thead>
          <tr>
            <th scope="col">Claim</th>
            <th scope="col">Count</th>
            <th scope="col">Sample</th>
            <th scope="col">Period</th>
            <th scope="col">Status</th>
            <th scope="col">Source</th>
          </tr>
        </thead>
        <tbody>
          {evidence.map((item) => (
            <tr key={`${item.metric}-${item.period}-${item.count}`}>
              <td>
                {item.metric}
                {item.note ? <span className="fine-print">{item.note}</span> : null}
              </td>
              <td>{item.count}</td>
              <td>{item.sample}</td>
              <td>{item.period}</td>
              <td>
                <CaseStatusBadge status={item.status} />
              </td>
              <td>{item.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableFrame>
  );
}
