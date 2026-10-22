import Link from "next/link";
import { CaseEvidenceTable } from "@/components/CaseEvidenceTable";
import { CaseStatusBadge } from "@/components/CaseStatusBadge";
import type { CaseClaim } from "@/lib/data";

const DOMAIN_LABELS: Record<string, string> = {
  matchday: "On the pitch",
  off_pitch: "Off the pitch",
  chairman: "The chairman's record",
};

export function CaseClaimCard({
  claim,
  compact = false,
}: {
  claim: CaseClaim;
  compact?: boolean;
}) {
  return (
    <article
      className="case-claim"
      id={`claim-${claim.id.replaceAll("_", "-")}`}
      data-contract="case.claim"
    >
      <div className="case-claim-head">
        <div>
          <p className="eyebrow">{DOMAIN_LABELS[claim.domain] ?? claim.domain}</p>
          <h2>{claim.title}</h2>
        </div>
        <span data-contract="case.claim.status">
          <CaseStatusBadge status={claim.status} />
        </span>
      </div>

      <p className="case-claim-sentence">{claim.claim}</p>
      <p className="case-count" data-contract="case.claim.count">
        <span className="case-label">The count</span>
        {claim.count}
      </p>
      <p className="fine-print">{claim.status_reason}</p>

      {!compact ? <CaseEvidenceTable evidence={claim.evidence} /> : null}

      {!compact ? (
        <div className="case-two-col">
          <div>
            <h3>What better data would do</h3>
            <p>{claim.better_data}</p>
          </div>
          <div data-contract="case.claim.change">
            <h3>What would change the view</h3>
            <p>{claim.change_mind}</p>
          </div>
        </div>
      ) : null}

      <div className="case-links">
        {claim.links.map((link) => (
          <Link className="text-link" href={link.href} key={link.href}>
            {link.label} →
          </Link>
        ))}
        {compact ? (
          <Link
            className="text-link"
            href={`/analysis/#claim-${claim.id.replaceAll("_", "-")}`}
          >
            Full evidence →
          </Link>
        ) : null}
      </div>
    </article>
  );
}
