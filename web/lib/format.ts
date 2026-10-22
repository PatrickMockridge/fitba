export function formatDate(value: string): string {
  const day = value.includes("T") ? value.slice(0, 10) : value;
  const date = new Date(`${day}T12:00:00Z`);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * Shared display formatting.
 *
 * Production values are rounded once in the pipeline according to the metric
 * registry. These helpers only render an already-published value; use them
 * instead of scattering Math.round/toFixed through components.
 */

export function formatInteger(value: number): string {
  return String(Math.round(value));
}

export function formatPercent(share: number): string {
  return `${formatInteger(share * 100)}%`;
}

export function formatPercentValue(value: number, digits = 0): string {
  return `${value.toFixed(digits)}%`;
}

export function formatDecimal(value: number, digits = 2): string {
  return value.toFixed(digits);
}
