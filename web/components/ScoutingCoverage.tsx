import Link from "next/link";
import { formatInteger } from "@/lib/format";

export function ScoutingCoverage({
  totals,
  knownGaps,
  sources,
}: {
  totals: Record<string, number>;
  knownGaps: string[];
  sources: Array<{ id: string; name: string; url: string; coverage?: string }>;
}) {
  return (
    <>
      <div className="stat-row four">
        <div className="stat-tile">
          <span className="stat-label">Leagues</span>
          <span className="stat-value">{formatInteger(totals.leagues ?? 0)}</span>
          <span className="stat-note">configured universe</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Searchable</span>
          <span className="stat-value">{formatInteger(totals.searchable ?? 0)}</span>
          <span className="stat-note">with rated players</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Players</span>
          <span className="stat-value">{formatInteger(totals.players ?? 0)}</span>
          <span className="stat-note">provider season rows</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Rated</span>
          <span className="stat-value">{formatInteger(totals.rated ?? 0)}</span>
          <span className="stat-note">provider rating present</span>
        </div>
      </div>
      <div className="grid two-col">
        <section className="mini-block">
          <h3>Known gaps</h3>
          <ul className="plain-list">
            {knownGaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </section>
        <section className="mini-block">
          <h3>Sources</h3>
          <ul className="plain-list">
            {sources.map((source) => (
              <li key={source.id}>
                <a className="text-link" href={source.url} rel="noreferrer">
                  {source.name}
                </a>
                {source.coverage ? <span className="muted"> · {source.coverage}</span> : null}
              </li>
            ))}
          </ul>
          <p className="fine-print">
            Raw provider responses stay in the local cache and are never published. The
            published record is derived. See <Link href="/sources/">sources and licences</Link>{" "}
            and <Link href="/methodology/">the method</Link>.
          </p>
        </section>
      </div>
    </>
  );
}
