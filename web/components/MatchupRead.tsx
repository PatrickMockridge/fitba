import type { MatchdayRead } from "@/lib/data";

const BASIS_LABEL: Record<string, string> = {
  measured: "Measured",
  inferred: "Inferred",
  unknown: "Unknown",
};

function Basis({ value }: { value: string }) {
  return (
    <span
      className={`basis-badge basis-${value}`}
      data-contract-indicator="basis"
    >
      {BASIS_LABEL[value] ?? value}
    </span>
  );
}

export function MatchupRead({
  read,
  contract,
}: {
  read: MatchdayRead;
  contract?: string;
}) {
  return (
    <section className="matchday-read" data-contract={contract}>
      <p className="eyebrow">The read</p>
      <h2>{read.headline}</h2>
      <ul className="read-list">
        {read.bullets.map((bullet, index) => (
          <li className="read-bullet" key={`${bullet.text}-${index}`}>
            <Basis value={bullet.basis} />
            <span>{bullet.text}</span>
          </li>
        ))}
      </ul>
      {read.keys.length ? (
        <>
          <h3 className="keys-title">Keys to the match</h3>
          <div className="keys-grid">
            {read.keys.map((key) => (
              <article className="key-card" key={`${key.label}-${key.text}`}>
                <div className="key-head">
                  <h4>{key.label}</h4>
                  <Basis value={key.basis} />
                </div>
                <p>{key.text}</p>
              </article>
            ))}
          </div>
        </>
      ) : null}
      <p className="fine-print">{read.note}</p>
    </section>
  );
}
