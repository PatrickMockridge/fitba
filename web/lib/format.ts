export function formatDate(value: string): string {
  const day = value.includes("T") ? value.slice(0, 10) : value;
  const date = new Date(`${day}T12:00:00Z`);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function pct(value: unknown): string {
  if (typeof value !== "number") return "—";
  return `${Math.round(value * 100)}%`;
}

const TERMS: Array<[RegExp, string]> = [
  [/\bAM\/WM\b/g, "attacking midfielders"],
  [/\bFB\/WB\b/g, "full-backs/wing-backs"],
  [/\bCB\b/g, "centre-back"],
  [/\bGK\b/g, "goalkeepers"],
  [/\bST\b/g, "strikers"],
  [/\bW\b/g, "wingers"],
  [/\bU21\b/g, "under-21"],
];

export function plainText(value: string): string {
  let output = value;
  for (const [pattern, replacement] of TERMS) {
    output = output.replace(pattern, replacement);
  }
  return output;
}
