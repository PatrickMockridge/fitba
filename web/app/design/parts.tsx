import type { ReactNode } from "react";

type Tone = "ok" | "warn" | "danger" | "neutral" | "info" | "club";

export function DsBadge({
  children,
  tone = "neutral",
  title,
}: {
  children: ReactNode;
  tone?: Tone;
  title?: string;
}) {
  return (
    <span className={`ds-badge ds-badge--${tone}`} title={title}>
      {children}
    </span>
  );
}

export function DsStat({
  label,
  value,
  note,
}: {
  label: string;
  value: ReactNode;
  note?: string;
}) {
  return (
    <div className="ds-stat">
      <span className="ds-stat__label">{label}</span>
      <span className="ds-stat__value">{value}</span>
      {note ? <span className="ds-stat__note">{note}</span> : null}
    </div>
  );
}

const FORM_LABELS: Record<string, string> = {
  W: "win",
  D: "draw",
  L: "loss",
};

export function DsFormStrip({ form }: { form: string }) {
  if (!form) {
    return <span className="ds-badge ds-badge--neutral">No form</span>;
  }
  return (
    <span
      className="ds-form-strip"
      aria-label={`Recent form: ${form
        .split("")
        .map((result) => FORM_LABELS[result] ?? result)
        .join(", ")}`}
    >
      {form.split("").map((result, index) => (
        <span
          key={`${result}-${index}`}
          className={`ds-form-chip ds-form-chip--${result.toLowerCase()}`}
        >
          {result}
        </span>
      ))}
    </span>
  );
}

export function DsMeter({
  label,
  value,
  max = 100,
}: {
  label: string;
  value: number;
  max?: number;
}) {
  const percentage = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="ds-meter">
      <div className="ds-meter__head">
        <span>{label}</span>
        <span>
          {value} / {max}
        </span>
      </div>
      <div
        className="ds-meter__track"
        role="progressbar"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <span className="ds-meter__fill" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

export function sourceLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "source";
  }
}
