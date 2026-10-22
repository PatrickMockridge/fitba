export function formatDate(value: string): string {
  const day = value.includes("T") ? value.slice(0, 10) : value;
  const date = new Date(`${day}T12:00:00Z`);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
