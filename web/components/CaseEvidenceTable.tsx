import { CaseStatusBadge } from "@/components/CaseStatusBadge";
import type { CaseEvidence } from "@/lib/data";

export function CaseEvidenceTable({ evidence }: { evidence: CaseEvidence[] }) {
  return (
    <div className="table-wrap" data-contract="case.claim.evidence">
      <table className="league-table case-evidence">
<caption className="fine-print">Claim evidence with count, sample, period, status and source.</caption>
        <thead>
          <tr>
            <th>Claim</th>
            <th>Count</th>
            <th>Sample</th>
            <th>Period</th>
            <th>Status</th>
            <th>Source</th>
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
    </div>
  );
}
