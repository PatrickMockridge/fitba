import { formatDate, formatDecimal, formatInteger, formatPercentValue } from "@/lib/format";
import type { ManagerMarketFile } from "@/lib/data";

const STATUS_LABEL: Record<string, string> = {
  priced_and_mentioned: "Priced + mentioned",
  priced: "Priced",
  mentioned: "Mentioned",
};

export function ManagerMarketPanel({ data }: { data: ManagerMarketFile | null }) {
  if (!data) {
    return (
      <section className="card" data-contract="rumours.manager-market">
        <div className="section-head">
          <div>
            <p className="eyebrow">Next manager</p>
            <h2>Next-manager market</h2>
          </div>
          <span className="badge badge-neutral">Unavailable</span>
        </div>
        <p className="fine-print" data-contract-indicator="unknown">
          The next-manager market is not published in this build.
        </p>
        <p className="fine-print">
          Not betting advice. No affiliate or advertising relationship.
        </p>
      </section>
    );
  }
  const market = data.market;
  const gate = market.gate;
  const open = market.state === "open";
  const stale = market.freshness.stale;
  const withheld = market.coverage.status === "withheld";
  const sourceUrl = market.source_urls[0] ?? null;

  return (
    <section className="card" data-contract="rumours.manager-market">
      <div className="section-head">
        <div>
          <p className="eyebrow">Next manager · market intelligence</p>
          <h2>{market.label}</h2>
        </div>
        <span className={`badge ${open ? "badge-warn" : "badge-neutral"}`}>
          {open ? "Vacancy" : market.state === "closed" ? "Closed" : "Unavailable"}
        </span>
      </div>

      <p className="fine-print">
        <strong>Not betting advice.</strong> No affiliate or advertising relationship.
        Odds are published only while Aberdeen have no permanent manager; the
        section closes when a permanent manager is appointed.
      </p>

      {open ? (
        <>
          <p className="fine-print">
            <strong>Gate:</strong>{" "}
            {gate.permanent_manager
              ? `permanent manager ${gate.permanent_manager}`
              : `no permanent manager; ${gate.interim_manager ?? "an interim"} in charge since ${
                  gate.interim_since ? formatDate(gate.interim_since) : "—"
                }`}
            {gate.vacancy_started
              ? ` · vacancy started ${formatDate(gate.vacancy_started)}`
              : ""}
            .
          </p>
          <p className="fine-print">
            <strong>Snapshot:</strong> {market.bookmaker ?? "—"}
            {market.publisher ? ` · ${market.publisher}` : ""}
            {market.observed_at ? ` · observed ${formatDate(market.observed_at)}` : ""}
            {stale ? (
              <span className="badge badge-warn"> Snapshot stale</span>
            ) : null}
            {withheld ? (
              <span className="badge badge-warn"> Prices withheld</span>
            ) : null}
            {sourceUrl ? (
              <>
                {" · "}
                <a className="text-link" href={sourceUrl} target="_blank" rel="noreferrer">
                  Source
                </a>
              </>
            ) : null}
          </p>
          {!withheld ? (
            <div className="table-wrap">
              <table className="league-table compact">
                <caption className="fine-print">
                  {market.bookmaker ?? "Bookmaker list"} · single public snapshot.
                  Raw implied probability is 1 / decimal odds and is not a
                  probability of appointment.{" "}
                  {market.coverage.note}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Candidate</th>
                    <th scope="col">Current role</th>
                    <th scope="col" className="num">Fractional</th>
                    <th scope="col" className="num">Decimal</th>
                    <th scope="col" className="num">Raw implied</th>
                    <th scope="col" className="num">DonsTalk mentions</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.candidates.map((candidate) => (
                    <tr key={candidate.candidate_id}>
                      <td className="strong">{candidate.name}</td>
                      <td>
                        {candidate.current_role ?? candidate.current_club ?? "—"}
                      </td>
                      <td className="num">
                        {candidate.odds ? candidate.odds.fractional : "—"}
                      </td>
                      <td className="num">
                        {candidate.odds ? formatDecimal(candidate.odds.decimal, 2) : "—"}
                      </td>
                      <td className="num">
                        {candidate.odds
                          ? formatPercentValue(candidate.odds.implied_probability * 100, 1)
                          : "—"}
                      </td>
                      <td className="num">
                        {candidate.mentions ? formatInteger(candidate.mentions.count) : "—"}
                      </td>
                      <td>
                        {candidate.odds
                          ? STATUS_LABEL[candidate.status] ?? candidate.status
                          : "DonsTalk mention only"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="fine-print">{market.coverage.note}</p>
          )}
          <p className="fine-print">
            {market.coverage.field_complete && market.coverage.overround !== null
              ? `Field complete; raw implied overround ${formatPercentValue(
                  market.coverage.overround * 100,
                  1,
                )}.`
              : "Partial field; raw implied values do not sum to 100% and no overround is published."}{" "}
            {market.coverage.priced_count} priced · {market.coverage.mentioned_count}{" "}
            mentioned.
          </p>
        </>
      ) : (
        <p className="fine-print" data-contract-indicator="unknown">
          {market.state === "closed"
            ? `Closed — permanent manager appointed${
                gate.permanent_manager ? `: ${gate.permanent_manager}` : ""
              }${gate.permanent_manager_start ? ` on ${formatDate(gate.permanent_manager_start)}` : ""}. No odds are published while a permanent manager is in post.`
            : gate.reason ?? "The staff register is not a valid vacancy; no odds are published."}
        </p>
      )}
      <p className="fine-print">{data.disclaimer}</p>
    </section>
  );
}
