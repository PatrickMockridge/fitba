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

export function formatSigned(value: number, digits = 2): string {
  const text = value.toFixed(digits);
  return value > 0 ? `+${text}` : text;
}

export function formatInterval(
  low: number | null | undefined,
  high: number | null | undefined,
  digits = 2,
): string {
  if (low === null || low === undefined || high === null || high === undefined) {
    return "—";
  }
  return `${formatDecimal(low, digits)}–${formatDecimal(high, digits)}`;
}

export function formatGbp(value: number): string {
  if (value >= 1_000_000) {
    return `£${(value / 1_000_000).toFixed(value >= 10_000_000 ? 1 : 2)}m`;
  }
  return `£${Math.round(value / 1000)}k`;
}

export function formatGbpBand(
  low: number | null | undefined,
  high: number | null | undefined,
): string {
  if (low === null || low === undefined || high === null || high === undefined) {
    return "—";
  }
  return `${formatGbp(low)}–${formatGbp(high)}`;
}
