export type RoseStatus = "available" | "partial" | "unavailable";

export type RoseUnit = "per90" | "percent";

export type RoseDirection = "positive" | "negative";

export interface RoseAxis {
  metric: string;
  value: number | null;
  percentile: number | null;
  cohort_n: number;
}

export interface RoseFigure {
  id: "overall" | "position";
  label: string;
  status: RoseStatus;
  axes: RoseAxis[];
}

export interface RoseBlock {
  status: RoseStatus;
  reason: string | null;
  league: string;
  league_label: string;
  minutes: number;
  min_minutes: number;
  cohort_min_minutes: number;
  basis: "role_family" | "provider_group" | "insufficient";
  cohort_n: number;
  figures: RoseFigure[];
  season_used: string | null;
  cohort_season: string | null;
  fallback: boolean;
  fallback_reason: string | null;
  fallback_note: string | null;
}

export interface RoseCatalogueEntry {
  label: string;
  short?: string;
  unit: RoseUnit;
  direction: RoseDirection;
}

export type RoseCatalogue = Record<string, RoseCatalogueEntry>;
