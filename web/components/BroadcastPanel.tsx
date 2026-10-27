import Link from "next/link";
import type { BroadcastFixture, BroadcastRegion } from "@/lib/data";
import { regionLabel } from "@/lib/broadcast";
import { formatDate } from "@/lib/format";

function statusClass(status: string): string {
  if (status === "confirmed") return "badge badge-ok";
  if (status === "blackout_window") return "badge badge-neutral";
  return "badge badge-neutral";
}

function accessLabel(access: string): string {
  if (access === "ppv") return "PPV";
  if (access === "live") return "Live";
  return "Replay";
}

function mediumLabel(medium: string): string {
  return medium === "audio" ? "Audio" : "Video";
}

function RegionRow({
  label,
  region,
  redtvUrl,
}: {
  label: string;
  region: BroadcastRegion;
  redtvUrl: string;
}) {
  return (
    <div className="broadcast-region">
      <p className="eyebrow">{label}</p>
      <div className="badge-row">
        <span className={statusClass(region.status)}>{regionLabel(region.status)}</span>
        {region.outlets.map((outlet) => (
          <span
            className="badge badge-neutral"
            key={`${outlet.platform}-${outlet.medium}-${outlet.access}`}
          >
            {outlet.platform} · {mediumLabel(outlet.medium)} ·{" "}
            {accessLabel(outlet.access)}
          </span>
        ))}
      </div>
      <p className="fine-print">{region.note}</p>
      {region.status !== "confirmed" && label === "International" ? (
        <p className="fine-print">
          <Link className="text-link" href={redtvUrl}>
            RedTV
          </Link>{" "}
          carries the club&apos;s streaming service; availability is set per
          fixture and region.
        </p>
      ) : null}
      {region.status === "unknown" || region.basis !== "official_source" ? (
        <span className="visually-hidden" data-contract-indicator="unknown">
          Unknown or unconfirmed broadcast state
        </span>
      ) : null}
    </div>
  );
}

export function BroadcastPanel({
  row,
  redtvUrl,
}: {
  row: BroadcastFixture | null | undefined;
  redtvUrl: string;
}) {
  return (
    <section className="card broadcast-panel" data-contract="matchday.watch">
      <div className="section-head">
        <div>
          <p className="eyebrow">Television and streaming</p>
          <h2>How to watch</h2>
        </div>
        <span className="badge badge-neutral">Official sources only</span>
      </div>
      {!row ? (
        <p className="fine-print">
          No broadcast row is published for this fixture. This does not mean the
          match is not televised.
        </p>
      ) : (
        <>
          <div className="broadcast-grid">
            <RegionRow
              label="UK & Ireland"
              region={row.domestic}
              redtvUrl={redtvUrl}
            />
            <RegionRow
              label="International"
              region={row.international}
              redtvUrl={redtvUrl}
            />
          </div>
          <p className="fine-print" data-contract-indicator="source">
            {row.state === "curated"
              ? "Curated from an official club or SPFL page."
              : row.state === "fixture_conflict" || row.state === "source_conflict"
                ? "Broadcast details are withheld until the fixture or source is re-verified."
                : "Rule-based state; no fixture broadcast listing has been checked for this match."}
          </p>
          {row.sources.length ? (
            <p className="fine-print">
              Source:{" "}
              {row.sources.map((source, index) => (
                <span key={`${source.source_id}-${source.url}`}>
                  {index ? " · " : null}
                  <Link className="text-link" href={source.url}>
                    {source.title}
                  </Link>
                  {" "}
                  · checked {formatDate(source.verified_at)}
                </span>
              ))}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
