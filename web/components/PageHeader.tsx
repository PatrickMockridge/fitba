import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  summary,
  meta,
  actions,
}: {
  eyebrow?: string;
  title: string;
  summary?: string;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className="page-head page-header">
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h1>{title}</h1>
      {summary ? <p className="page-summary">{summary}</p> : null}
      {meta ? <div className="page-meta">{meta}</div> : null}
      {actions ? <div className="hero-actions">{actions}</div> : null}
    </section>
  );
}
