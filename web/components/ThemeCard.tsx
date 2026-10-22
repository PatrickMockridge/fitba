import Link from "next/link";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import type { ThemeBlock } from "@/lib/data";

function horizonLabel(theme: ThemeBlock) {
  return theme.horizon === "mission" ? "Cormack-era mission" : "Current season";
}

function readLabel(theme: ThemeBlock) {
  return theme.read_basis === "curated" ? "Curated read" : "Inferred read";
}

function anchor(theme: ThemeBlock) {
  return theme.theme_id.replaceAll("_", "-");
}

export function ThemeCard({
  theme,
  compact = false,
  contract,
}: {
  theme: ThemeBlock;
  compact?: boolean;
  contract?: string;
}) {
  const mission = theme.horizon === "mission";
  return (
    <article
      className={`theme-card${compact ? " is-compact" : ""}${mission ? " is-mission" : ""}`}
      id={anchor(theme)}
      data-contract={contract}
    >
      <div className="theme-card-head">
        <div>
          <p className="eyebrow">{horizonLabel(theme)}</p>
          <h3>{theme.title}</h3>
        </div>
        <div className="badge-row">
          {theme.status !== "available" ? (
            <span className="badge badge-warn">{theme.status}</span>
          ) : null}
          <ConfidenceBadge confidence={theme.confidence} compact />
        </div>
      </div>

      <h4 className="theme-headline">{theme.headline ?? theme.title}</h4>
      {theme.fan_question ? (
        <p className="theme-question">
          <span className="muted">The question:</span> {theme.fan_question}
        </p>
      ) : null}

      {theme.read ? (
        <p className="theme-read">
          <span
            className={`basis-badge basis-${theme.read_basis}`}
            data-contract-indicator="basis"
          >
            The read · {readLabel(theme)}
          </span>{" "}
          {theme.read}
        </p>
      ) : null}

      {theme.status !== "available" && theme.reason ? (
        <p className="fine-print">Unavailable: {theme.reason.replaceAll("_", " ")}.</p>
      ) : null}

      <div className="evidence-chips" data-contract="themes.evidence">
        {theme.evidence.slice(0, compact ? 3 : 5).map((item) => (
          <span className="evidence-chip" key={`${item.label}-${item.value}`}>
            <span className="evidence-label">{item.label}</span>
            <span className="evidence-value">
              {item.value === null || item.value === undefined ? "—" : String(item.value)}
            </span>
            {item.note ? <span className="evidence-note">{item.note}</span> : null}
          </span>
        ))}
      </div>

      {theme.implications?.length ? (
        <div className="theme-implications" data-contract="themes.implications">
          <p className="eyebrow">Transfer implication</p>
          {theme.implications.map((implication) => (
            <p key={`${implication.family}-${implication.category}`}>
              <Link className="text-link" href={implication.href}>
                {implication.line}
              </Link>
            </p>
          ))}
        </div>
      ) : null}

      <div className="theme-links">
        {theme.links.map((link) => (
          <Link className="text-link" href={link.href} key={link.href}>
            {link.label} →
          </Link>
        ))}
        {compact ? (
          <Link className="text-link" href={`/themes/#${anchor(theme)}`}>
            Full evidence →
          </Link>
        ) : null}
      </div>

      {!compact && theme.caveats.length ? (
        <details className="theme-details">
          <summary>Caveats and method</summary>
          <ul className="plain-list">
            {theme.caveats.map((caveat) => (
              <li key={caveat}>{caveat}</li>
            ))}
          </ul>
          {theme.method ? <p className="fine-print">{theme.method}</p> : null}
        </details>
      ) : null}
    </article>
  );
}
