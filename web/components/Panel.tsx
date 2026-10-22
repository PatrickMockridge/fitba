import type { ReactNode } from "react";
import type { Panel as PanelModel } from "@/lib/player-page";

export function Panel({
  panel,
  id,
  children,
}: {
  panel: PanelModel<unknown>;
  id?: string;
  children: ReactNode;
}) {
  return (
    <section className="data-panel" id={id}>
      <div className="data-panel-head">
        <div>
          <p className="eyebrow">{panel.eyebrow}</p>
          <h2>{panel.title}</h2>
        </div>
        {panel.badge ? <span className="badge badge-neutral">{panel.badge}</span> : null}
      </div>
      {panel.status === "unavailable" || panel.status === "not_applicable" ? (
        <p>{panel.note ?? "No data is available for this panel."}</p>
      ) : (
        children
      )}
      {panel.warnings.length ? (
        <p className="fine-print">
          {panel.warnings.map((warning) => warning.message).join(" ")}
        </p>
      ) : null}
    </section>
  );
}
