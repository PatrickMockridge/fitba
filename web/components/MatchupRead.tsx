import type { MatchdayRead } from "@/lib/data";

export function MatchupRead({ read }: { read: MatchdayRead }) {
  return (
    <section className="matchday-read">
      <p className="eyebrow">The read</p>
      <h2>{read.headline}</h2>
      <ul className="read-list">
        {read.bullets.slice(0, 3).map((bullet, index) => (
          <li className="read-bullet" key={`${bullet.text}-${index}`}>
            <span>{bullet.text}</span>
          </li>
        ))}
      </ul>
      {read.keys.length ? (
        <>
          <h3 className="keys-title">Keys to the match</h3>
          <div className="keys-grid">
            {read.keys.slice(0, 3).map((key) => (
              <article className="key-card" key={`${key.label}-${key.text}`}>
                <h4>{key.label}</h4>
                <p>{key.text}</p>
              </article>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
