export const FAMILY_ORDER: Record<string, number> = {
  goalkeeper: 0,
  centre_back: 1,
  full_back: 2,
  wing_back: 3,
  defensive_midfield: 4,
  central_midfield: 5,
  attacking_midfield: 6,
  wide_midfield: 7,
  wide_forward: 8,
  centre_forward: 9,
};

export const FAMILY_LABELS: Record<string, string> = {
  goalkeeper: "Goalkeeper",
  centre_back: "Centre back",
  full_back: "Full-back",
  wing_back: "Wing-back",
  defensive_midfield: "Defensive mid",
  central_midfield: "Centre mid",
  attacking_midfield: "Attacking mid",
  wide_midfield: "Wide mid",
  wide_forward: "Winger",
  centre_forward: "Centre forward",
  unknown: "No role observed",
};

export const FAMILY_SHORT_LABELS: Record<string, string> = {
  goalkeeper: "GK",
  centre_back: "CB",
  full_back: "FB",
  wing_back: "WB",
  defensive_midfield: "DM",
  central_midfield: "CM",
  attacking_midfield: "AM",
  wide_midfield: "WM",
  wide_forward: "W",
  centre_forward: "ST",
  unknown: "—",
};

export const SLOT_ORDER: Record<string, number> = {
  GK: 0,
  D_C: 1,
  D_WB_L: 2,
  D_WB_R: 3,
  DM_C: 4,
  M_C: 5,
  AM_C: 6,
  M_L: 7,
  M_R: 8,
  AM_L: 9,
  AM_R: 10,
  ST_C: 11,
};

export const FAMILY_COLORS: Record<string, string> = {
  goalkeeper: "#6b7280",
  centre_back: "#1d4ed8",
  full_back: "#2563eb",
  wing_back: "#3b82f6",
  defensive_midfield: "#047857",
  central_midfield: "#059669",
  attacking_midfield: "#10b981",
  wide_midfield: "#b45309",
  wide_forward: "#d97706",
  centre_forward: "#b91c1c",
};

export const SCOPE_LABELS: Record<string, string> = {
  aberdeen: "Aberdeen",
  previous_club: "Previous club",
  loan_club: "Loan club",
  national_team: "National team",
  unknown: "Unknown",
};

export const FAMILY_GROUPS: Record<string, string> = {
  goalkeeper: "goalkeeper",
  centre_back: "defence",
  full_back: "defence",
  wing_back: "defence",
  defensive_midfield: "midfield",
  central_midfield: "midfield",
  attacking_midfield: "midfield",
  wide_midfield: "midfield",
  wide_forward: "attack",
  centre_forward: "attack",
};

export function familyBroadGroups(family: string | null | undefined): string[] {
  switch (family) {
    case "goalkeeper":
      return ["goalkeeper"];
    case "centre_back":
      return ["defender"];
    case "full_back":
    case "wing_back":
      return ["defender", "midfielder"];
    case "defensive_midfield":
    case "central_midfield":
    case "attacking_midfield":
    case "wide_midfield":
      return ["midfielder"];
    case "wide_forward":
    case "centre_forward":
      return ["attacker"];
    default:
      return [];
  }
}

export function familySide(
  family: string | null | undefined,
  side: string | null | undefined,
): "left" | "centre" | "right" | null {
  if (side === "left" || side === "right" || side === "central") {
    return side === "central" ? "centre" : side;
  }
  if (family === "goalkeeper") return null;
  return family === "wide_midfield" || family === "wide_forward" ? null : "centre";
}

export function slotColor(groups: string[]): string {
  if (groups.includes("goalkeeper")) return "#6b7280";
  if (groups.includes("defender")) return "#1d4ed8";
  if (groups.includes("midfielder")) return "#059669";
  if (groups.includes("attacker")) return "#b91c1c";
  return "#6b7280";
}

export function familyLabel(family: string | null | undefined): string {
  return FAMILY_LABELS[family ?? "unknown"] ?? family ?? "Unknown";
}

export function familyOrder(family: string | null | undefined): number {
  return FAMILY_ORDER[family ?? ""] ?? 99;
}

export function heatOpacity(share: number): number {
  if (share <= 0) return 0;
  return Math.min(1, Math.max(0.12, Number(share.toFixed(2))));
}
