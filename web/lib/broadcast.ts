import type { BroadcastDocument, BroadcastFixture } from "@/lib/data";

export function broadcastByFixture(
  document: BroadcastDocument | null,
): Record<string, BroadcastFixture> {
  return Object.fromEntries(
    (document?.fixtures ?? []).map((row) => [row.fixture_id, row]),
  );
}

export function watchLabel(row: BroadcastFixture | undefined | null): string {
  if (!row) return "—";
  if (row.state === "fixture_conflict" || row.state === "source_conflict") {
    return "Check fixture";
  }
  if (row.domestic.status === "blackout_window") return "UK blackout";
  if (row.domestic.status === "not_announced") return "Not announced";
  if (row.domestic.status !== "confirmed") return "—";
  const outlets = row.domestic.outlets;
  if (!outlets.length) return "Confirmed";
  return outlets
    .map((outlet) =>
      outlet.access === "ppv" ? `${outlet.platform} PPV` : outlet.platform,
    )
    .join(", ");
}

export function regionLabel(status: string): string {
  switch (status) {
    case "confirmed":
      return "Confirmed";
    case "blackout_window":
      return "UK blackout";
    case "not_announced":
      return "Not announced";
    default:
      return "Unknown";
  }
}
