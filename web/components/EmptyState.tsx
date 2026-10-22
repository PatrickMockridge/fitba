import type { ReactNode } from "react";

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <section className="empty-state">
      <h1>{title}</h1>
      <p>{body}</p>
      {action ? <div className="hero-actions">{action}</div> : null}
    </section>
  );
}
