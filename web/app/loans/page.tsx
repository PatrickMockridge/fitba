import Link from "next/link";
import { EmptyState } from "@/components/EmptyState";
import { LegendDisclosure } from "@/components/LegendDisclosure";
import { MetricStrip } from "@/components/MetricStrip";
import { PageHeader } from "@/components/PageHeader";
import { PlayerLink } from "@/components/PlayerLink";
import { TableFrame, Th } from "@/components/TableFrame";
import { formatDate } from "@/lib/format";
import { getTransfers, type TransferRecord } from "@/lib/data";

export const metadata = { title: "Loans · fitba" };

function LoanTable({ loans, label }: { loans: TransferRecord[]; label: string }) {
  if (!loans.length) {
    return <p className="muted">No confirmed loans in this group.</p>;
  }
  return (
    <TableFrame
      label={`${label} loan register`}
      caption={label}
      className="league-table compact register-table stack-mobile"
    >
      <thead>
        <tr>
          <Th>Player</Th>
          <Th>Club</Th>
          <Th>Window</Th>
          <Th>End</Th>
          <Th>Status</Th>
        </tr>
      </thead>
      <tbody>
        {loans.map((loan) => (
          <tr key={loan.transfer_id}>
            <td data-label="Player">
              <PlayerLink name={loan.player_name} href={loan.player_href} />
            </td>
            <td data-label="Club">
              {loan.direction === "out" ? loan.to_club_name : loan.from_club_name}
            </td>
            <td data-label="Window">
              {loan.season} · {loan.window}
            </td>
            <td data-label="End">
              {loan.loan_end_date ? formatDate(loan.loan_end_date) : "—"}
            </td>
            <td data-label="Status">
              {loan.verification_status === "confirmed" ? "Confirmed" : "Curated"}
            </td>
          </tr>
        ))}
      </tbody>
    </TableFrame>
  );
}

export default function LoansPage() {
  const data = getTransfers();
  if (!data) {
    return (
      <EmptyState
        title="No loan register published"
        body="The loan register is built from the confirmed transfer business and will appear after the next publish."
        action={
          <Link className="button button-ghost" href="/transfers/">
            Transfer register
          </Link>
        }
      />
    );
  }

  const season = data.season;
  const outNow = data.loans_out.filter((loan) => loan.season === season);
  const outEarlier = data.loans_out.filter((loan) => loan.season !== season);
  const inNow = data.loans_in.filter((loan) => loan.season === season);
  const inEarlier = data.loans_in.filter((loan) => loan.season !== season);

  return (
    <>
      <PageHeader
        eyebrow="Aberdeen · loans"
        title="Who is out on loan?"
        summary={`${data.loans_out.length} out and ${data.loans_in.length} in since 2019/20. ${outNow.length} out this season, ${inNow.length} in.`}
      />

      <MetricStrip
        columns={3}
        items={[
          { label: "Out", value: data.loans_out.length, note: "register" },
          { label: "In", value: data.loans_in.length, note: "register" },
          { label: "Out now", value: outNow.length, note: season },
        ]}
      />

      <section className="section">
        <div className="section-head">
          <h2>Out now</h2>
          <Link className="text-link" href="/squad/">
            Current squad →
          </Link>
        </div>
        <LoanTable loans={outNow} label={`Aberdeen players out on loan in ${season}`} />
        {outEarlier.length ? (
          <details className="page-legend">
            <summary>Earlier loans out ({outEarlier.length})</summary>
            <div className="page-legend-body">
              <LoanTable loans={outEarlier} label="Earlier Aberdeen loans out" />
            </div>
          </details>
        ) : null}
      </section>

      <section className="section">
        <div className="section-head">
          <h2>In now</h2>
        </div>
        <LoanTable loans={inNow} label={`Players borrowed in during ${season}`} />
        {inEarlier.length ? (
          <details className="page-legend">
            <summary>Earlier loans in ({inEarlier.length})</summary>
            <div className="page-legend-body">
              <LoanTable loans={inEarlier} label="Earlier players borrowed in" />
            </div>
          </details>
        ) : null}
      </section>

      <LegendDisclosure title="Loan terms and coverage">
        <p>
          Loan duration, recall and obligation terms are shown only when a public
          source confirms them; otherwise the end date is a dash. Every row is
          confirmed business from the transfer register.
        </p>
        <p>
          <Link href="/transfers/">Full transfer register</Link> ·{" "}
          <Link href="/methodology/">Method</Link> ·{" "}
          <Link href="/sources/">Sources</Link>
        </p>
      </LegendDisclosure>
    </>
  );
}
