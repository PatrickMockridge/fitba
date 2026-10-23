import type { ReactNode } from "react";

export function ProfileSection({
  id,
  eyebrow,
  title,
  badge,
  note,
  indicator,
  contract,
  children,
}: {
  id?: string;
  eyebrow: string;
  title: string;
  badge?: string | null;
  note?: string | null;
  indicator?: string;
  contract?: string;
  children: ReactNode;
}) {
  return (
    <section
      className="data-panel"
      id={id}
      data-contract={contract}
      data-contract-indicator={indicator}
    >
      <div className="data-panel-head">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        {badge ? <span className="badge badge-neutral">{badge}</span> : null}
      </div>
      {children}
      {note ? <p className="fine-print">{note}</p> : null}
    </section>
  );
}
