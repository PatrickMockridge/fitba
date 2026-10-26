import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import {
  getUnknowns,
  readGeneratedJson,
  type UnknownClass,
  type UnknownCount,
} from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/unknowns/" },
  title: "Unknowns register · fitba",
  description:
    "What the public record does not know, why, and which public source would resolve it. Unknown is a published state, not zero.",
};

const DOMAIN_ORDER = [
  "availability",
  "transfers",
  "contracts",
  "scouting",
  "player-profile",
  "former-players",
  "history",
  "matchday",
  "rumours",
  "club",
  "recruitment",
  "sources",
];

const DOMAIN_LABELS: Record<string, string> = {
  availability: "Availability",
  transfers: "Transfers and fees",
  contracts: "Contracts and sell-on",
  scouting: "Scouting and Europe",
  "player-profile": "Player profiles",
  "former-players": "Former players",
  history: "History",
  matchday: "Matchday",
  rumours: "Rumours and fan signal",
  club: "The club",
  recruitment: "Recruitment and needs",
  sources: "Sources and provider gates",
  other: "Other",
};

function countValue(count: UnknownCount): number | null {
  const document = readGeneratedJson<unknown>(count.payload);
  if (document === null || document === undefined) return null;
  let value: unknown = document;
  for (const raw of count.pointer.replace(/^\//, "").split("/")) {
    const token = raw.replaceAll("~1", "/").replaceAll("~0", "~");
    if (Array.isArray(value)) value = value[Number(token)];
    else if (value && typeof value === "object")
      value = (value as Record<string, unknown>)[token];
    else return null;
  }
  return typeof value === "number" ? value : null;
}

function UnknownCard({ item }: { item: UnknownClass }) {
  return (
    <article className="card unknown-card" id={`unknown-${item.id}`}>
      <div className="section-head">
        <div>
          <p className="eyebrow">{DOMAIN_LABELS[item.domain] ?? item.domain}</p>
          <h3>{item.label}</h3>
        </div>
        {item.no_public_source ? (
          <span className="badge badge-warn">No public source</span>
        ) : (
          <span className="badge badge-neutral">Resolvable</span>
        )}
      </div>
      <p>{item.description}</p>
      <p className="fine-print">
        <strong>Why it is unknown:</strong> {item.reason}
      </p>
      {item.no_public_source ? (
        <p className="fine-print" data-contract-indicator="unknown">
          No public source currently resolves this class. It stays labelled rather
          than being estimated.
        </p>
      ) : item.resolving_source ? (
        <p className="fine-print">
          Resolving source:{" "}
          <Link className="text-link" href={item.resolving_source.url}>
            {item.resolving_source.label}
          </Link>
          {item.resolving_source.note ? ` · ${item.resolving_source.note}` : ""}
        </p>
      ) : null}
      {item.count ? (
        <p className="fine-print">
          Published count: {countValue(item.count) ?? "—"} ·{" "}
          <Link className="text-link" href={`/glossary/#def-metric.${item.count.metric_id}`}>
            {item.count.metric_id}
          </Link>{" "}
          ·{" "}
          <code>
            {item.count.payload}
            {item.count.pointer}
          </code>
        </p>
      ) : null}
      <p className="fine-print">
        Affects:{" "}
        {item.surfaces.map((surface, index) => (
          <span key={surface.id}>
            {index ? " · " : null}
            <Link className="text-link" href={surface.path}>
              {surface.label}
            </Link>
          </span>
        ))}
      </p>
    </article>
  );
}

export default function UnknownsPage() {
  const document = getUnknowns();
  if (!document) {
    return (
      <ContractPage surface="unknowns" state="empty">
        <section className="page-head" data-contract="unknowns.hero">
          <p className="eyebrow">The record&apos;s limits</p>
          <h1>Unknowns register</h1>
          <p className="lede">No unknowns register is published in this build.</p>
        </section>
      </ContractPage>
    );
  }
  const noSource = document.classes.filter((item) => item.no_public_source);
  const domains = [...DOMAIN_ORDER, "other"].filter(
    (domain) =>
      document.classes.some((item) => item.domain === domain) ||
      (domain === "other" &&
        document.classes.some((item) => !DOMAIN_ORDER.includes(item.domain))),
  );

  return (
    <ContractPage surface="unknowns">
      <section className="page-head" data-contract="unknowns.hero">
        <p className="eyebrow">The record&apos;s limits</p>
        <h1>Unknowns register</h1>
        <p className="lede">
          What the public record does not know, why, and what would resolve it.
          Unknown is a published state, not zero. A class with no public source is
          labelled rather than estimated or requested from the club.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/sources/">
            Sources
          </Link>
          <Link className="button button-ghost" href="/glossary/">
            Glossary
          </Link>
          <Link className="button button-ghost" href="/metrics/">
            Metrics and audit
          </Link>
        </div>
        <p className="fine-print" data-contract-indicator="source">
          Reviewed {document.reviewed || "—"}. Counts come from registered published
          metrics; the register introduces no number.
        </p>
      </section>

      <section className="section" data-contract="unknowns.register">
        <div className="section-head">
          <div>
            <p className="eyebrow">Gaps by domain</p>
            <h2>What is not known</h2>
          </div>
          <span className="badge badge-neutral">{document.classes.length} classes</span>
        </div>
        <p>{document.owner_note}</p>
        {domains.map((domain) => (
          <section className="unknown-domain" key={domain}>
            <h3>{DOMAIN_LABELS[domain] ?? domain}</h3>
            <div className="unknown-grid">
              {document.classes
                .filter((item) =>
                  domain === "other"
                    ? !DOMAIN_ORDER.includes(item.domain)
                    : item.domain === domain,
                )
                .map((item) => (
                  <UnknownCard item={item} key={item.id} />
                ))}
            </div>
          </section>
        ))}
      </section>

      <section className="section" data-contract="unknowns.no-public-source">
        <div className="section-head">
          <div>
            <p className="eyebrow">Not available, not estimated</p>
            <h2>Classes with no public source</h2>
          </div>
          <span className="badge badge-warn">{noSource.length} classes</span>
        </div>
        <p>
          These gaps are not waiting on a better feed. The public record does not
          contain them, so fitba does not publish a value, a range or a guess.
        </p>
        <ul className="plain-list">
          {noSource.map((item) => (
            <li key={item.id}>
              <Link className="text-link" href={`#unknown-${item.id}`}>
                {item.label}
              </Link>
              <span className="muted"> · {item.reason}</span>
            </li>
          ))}
        </ul>
      </section>

      <p className="fine-print" data-contract="unknowns.sources">
        A gap is not a request to the club and not a target list. The source rules
        are on <Link href="/sources/">Sources</Link>; the definitions are on{" "}
        <Link href="/glossary/">Glossary</Link> and{" "}
        <Link href="/metrics/">Metrics and audit</Link>. Corrections are recorded
        on <Link href="/corrections/">Corrections and contact</Link>.
      </p>
    </ContractPage>
  );
}
