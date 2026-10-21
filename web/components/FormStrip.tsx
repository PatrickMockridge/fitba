const LABELS: Record<string, string> = { W: "win", D: "draw", L: "loss" };

export function FormStrip({ form }: { form: string }) {
  if (!form) return <span className="muted">—</span>;
  return (
    <span className="form-strip" aria-label={`Recent form: ${form.split("").map((c) => LABELS[c] ?? c).join(", ")}`}>
      {form.split("").map((result, index) => (
        <span key={`${result}-${index}`} className={`form-chip form-${result.toLowerCase()}`}>
          {result}
        </span>
      ))}
    </span>
  );
}
