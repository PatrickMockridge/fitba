import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { TransferCard } from "@/components/TransferCard";
import { getTransfers } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/loans/" }, title: "Loans · fitba" };

export default function LoansPage() {
  const data = getTransfers();
  if (!data) {
    return (
      <ContractPage surface="loans" state="empty">
        <section className="empty-state" data-contract="loans.empty">
          <h1>No loan register published</h1>
          <p>
            Run <code>uv run fitba transfers</code> and then{" "}
            <code>uv run fitba publish</code>.
          </p>
        </section>
      </ContractPage>
    );
  }

  return (
    <ContractPage surface="loans">
      <section className="page-head" data-contract="loans.hero">
        <p className="eyebrow">Aberdeen · confirmed loans</p>
        <h1>Loan register</h1>
        <p className="lede">
          Aberdeen players out on loan and players borrowed in. Every deal is
          confirmed business from the register; loan terms are shown only where an
          official source records them.
        </p>
        <div className="hero-actions">
          <span className="badge badge-neutral">
            {data.loan_scope?.register_current.out_count ?? data.loans_out.length} out
            in {data.loan_scope?.season ?? data.season}
          </span>
          <span className="badge badge-neutral">
            {data.loan_scope?.register_all_time.out_count ?? data.loans_out.length} out
            all-time
          </span>
          <span className="badge badge-neutral">
            {data.loan_scope?.official_list.out_count ?? "—"} on the official list
          </span>
          <span className="badge badge-warn" data-contract-indicator="unknown">
            terms often unknown
          </span>
        </div>
      </section>

      <section className="section" data-contract="loans.out">
        <div className="section-head">
          <div>
            <p className="eyebrow">Out</p>
            <h2>Aberdeen players on loan</h2>
          </div>
        </div>
        <div className="transfer-grid">
          {data.loans_out.map((loan) => (
            <TransferCard
              key={loan.transfer_id}
              transfer={loan}
              contract="loans.card"
            />
          ))}
        </div>
        {data.loans_out.length === 0 ? (
          <p className="muted">No confirmed loans out in this register.</p>
        ) : null}
      </section>

      <section className="section" data-contract="loans.in">
        <div className="section-head">
          <div>
            <p className="eyebrow">In</p>
            <h2>Players borrowed in</h2>
          </div>
        </div>
        <div className="transfer-grid">
          {data.loans_in.map((loan) => (
            <TransferCard
              key={loan.transfer_id}
              transfer={loan}
              contract="loans.card"
            />
          ))}
        </div>
        {data.loans_in.length === 0 ? (
          <p className="muted">No confirmed loans in in this register.</p>
        ) : null}
      </section>

      <section className="card" data-contract="loans.coverage">
        <div className="card-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>What we know about loan minutes</h2>
          </div>
        </div>
        <p>
          Premium-tier loans can be tracked through lineups and events where the
          licensed feed covers the loan club. League One/Two minutes use a curated
          match log; the page labels the coverage rather than pretending all tiers
          are equal.
        </p>
        {data.loan_scope?.reconciliation.register_only_out.length ? (
          <p className="fine-print">
            The register also lists{" "}
            {data.loan_scope.reconciliation.register_only_out
              .map((item) => item.player_name)
              .filter(Boolean)
              .join(", ")}{" "}
            on loan; they are not on the official men&apos;s team page and are not
            counted in the squad. See the{" "}
            <Link className="text-link" href="/squad/">
              squad page
            </Link>
            .
          </p>
        ) : null}
        <p className="fine-print" data-contract-indicator="unknown">
          Loan duration, recall and obligation terms are not in the transfer feed.
          They are shown only when confirmed by the club or a public record.
        </p>
        <Link className="text-link" href="/transfers/">
          Full transfer register →
        </Link>
      </section>
    </ContractPage>
  );
}
