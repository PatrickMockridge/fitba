import Link from "next/link";
import { PlayerLink } from "@/components/PlayerLink";
import type { Rumour } from "@/lib/data";
import { formatDate } from "@/lib/format";

const STATUS_CLASS: Record<string, string> = {
  active: "badge-warn",
  confirmed: "badge-ok",
  denied: "badge-neutral",
  stale: "badge-neutral",
};

const CONFIDENCE_CLASS: Record<string, string> = {
  high: "badge-ok",
  medium: "badge-warn",
  low: "badge-neutral",
};

const SOURCE_LABEL: Record<string, string> = {
  press: "Press",
  journalist: "Journalist",
  forum: "Forum",
  club: "Club",
};

const VALUE_LABEL: Record<string, string> = {
  free: "Free",
  loan: "Loan",
  "under-500k": "Under £500k",
  "500k-1m": "£500k–£1m",
  "1m-2m": "£1m–£2m",
  "2m-plus": "£2m+",
  unknown: "Value unknown",
};

function sourceLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "Source";
  }
}

export function RumourCard({ rumour }: { rumour: Rumour }) {
  const inbound = rumour.direction === "in";
  return (
    <article className={`rumour-card ${inbound ? "is-in" : "is-out"}`}>
      <div className="rumour-card-head">
        <span className={`badge ${STATUS_CLASS[rumour.status] ?? "badge-neutral"}`}>
          {rumour.status}
        </span>
        <span className={`badge ${CONFIDENCE_CLASS[rumour.confidence] ?? "badge-neutral"}`}>
          {rumour.confidence} confidence
        </span>
        <span className="badge badge-neutral">{inbound ? "IN" : "OUT"}</span>
      </div>

      <h3>
        <PlayerLink name={rumour.player_name} href={rumour.player_href} />
      </h3>
      <p className="rumour-meta">
        {rumour.position ?? "Position unknown"} ·{" "}
        {rumour.age ? `age ${rumour.age}` : "age unknown"} ·{" "}
        {rumour.current_club ?? "Club unknown"}
      </p>
      <p className="rumour-claim">{rumour.claim}</p>
      {rumour.player_mentions?.length ? (
        <p className="fine-print">
          Mentions:{" "}
          {rumour.player_mentions.map((mention, index) => (
            <span key={mention.href}>
              {index ? ", " : ""}
              <PlayerLink name={mention.name} href={mention.href} />
            </span>
          ))}
        </p>
      ) : null}

      <div className="rumour-facts">
        <span>{rumour.league ?? "League unknown"}</span>
        <span>{VALUE_LABEL[rumour.value_band] ?? rumour.value_band}</span>
        {rumour.last_seen ? <span>Last seen {formatDate(rumour.last_seen)}</span> : null}
      </div>

      {rumour.analysis_tags.length ? (
        <div className="pill-row">
          {rumour.analysis_tags.map((tag) => (
            <span className="pill" key={tag}>
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      <div className="rumour-sources">
        <span className="muted">
          {rumour.source_types.map((type) => SOURCE_LABEL[type] ?? type).join(" · ")}
        </span>
        {rumour.source_urls.map((url) => (
          <a key={url} href={url} target="_blank" rel="noreferrer">
            {sourceLabel(url)}
          </a>
        ))}
      </div>

      {rumour.status === "confirmed" && rumour.linked_transfer_id ? (
        <p className="fine-print">
          Confirmed — recorded in the{" "}
          <Link href="/transfers/">transfer register</Link>.
        </p>
      ) : (
        <p className="fine-print">Not confirmed business. Status is a lifecycle label, not a probability.</p>
      )}

      {/* TODO(engagement): votes, polls and submissions are a separate project.
          No local-only widget pretends to be a shared count. */}
    </article>
  );
}
