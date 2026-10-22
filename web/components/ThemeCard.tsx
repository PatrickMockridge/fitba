import Link from "next/link";
import { MetricStrip } from "@/components/MetricStrip";
import { ThemeMetrics } from "@/components/ThemeMetrics";
import { plainText } from "@/lib/format";
import type { ThemeBlock } from "@/lib/data";

function anchor(theme: ThemeBlock) {
  return theme.theme_id.replaceAll("_", "-");
}

export function ThemeCard({ theme }: { theme: ThemeBlock }) {
  const evidence = theme.evidence.slice(0, 3);
  const implication = theme.implications?.[0];

  return (
    <article className="theme-card" id={anchor(theme)}>
      <h3>{theme.title}</h3>
      <p className="theme-headline">{plainText(theme.headline ?? theme.title)}</p>

      {evidence.length ? (
        <MetricStrip
          columns={3}
          items={evidence.map((item) => ({
            label: plainText(item.label),
            value:
              item.value === null || item.value === undefined ? "—" : String(item.value),
            note: item.note ? plainText(item.note) : undefined,
          }))}
        />
      ) : null}

      {implication ? (
        <p className="theme-implication">
          <Link className="text-link" href={implication.href}>
            {implication.line}
          </Link>
        </p>
      ) : null}

      <details className="page-legend theme-evidence">
        <summary>Evidence and method</summary>
        <div className="page-legend-body">
          {theme.read ? <p>{plainText(theme.read)}</p> : null}
          <ul>
            {theme.evidence.map((item) => (
              <li key={`${item.label}-${item.value}`}>
                <strong>{item.label}:</strong> {String(item.value ?? "—")}
                {item.note ? ` — ${item.note}` : ""}
              </li>
            ))}
          </ul>
          {theme.caveats.length ? (
            <ul>
              {theme.caveats.map((caveat) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
          ) : null}
          {theme.method ? <p>{theme.method}</p> : null}
          <ThemeMetrics theme={theme} />
          <p>
            {theme.links.map((link) => (
              <span key={link.href}>
                <Link className="text-link" href={link.href}>
                  {link.label} →
                </Link>{" "}
              </span>
            ))}
          </p>
        </div>
      </details>
    </article>
  );
}
