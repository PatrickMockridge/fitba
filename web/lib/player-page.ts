import type {
  CareerRole,
  DisplayRole,
  PlayerPlayingTime,
  PlayerRole,
  SquadPositionStat,
  SquadStat,
  TacticalNote,
} from "@/lib/data";
import type { RoseBlock, RoseCatalogue } from "@/lib/rose";

export type DataStatus = "available" | "partial" | "unavailable" | "not_applicable";

export type WarningCode =
  | "COVERAGE_PARTIAL"
  | "SOURCE_MISSING"
  | "NO_ROLE_EVIDENCE"
  | "POSITION_UNKNOWN"
  | "OTHER_RECORDS_ONLY";

export interface PageWarning {
  code: WarningCode;
  message: string;
  field?: string;
}

export interface KnownValue<T> {
  status: "known" | "unknown" | "conflict";
  value: T | null;
  reason?: string | null;
  source?: {
    id: string;
    url?: string | null;
    verified_at?: string | null;
  } | null;
}

export type PanelId =
  | "profile"
  | "availability"
  | "position"
  | "playing_time"
  | "performance"
  | "recent_matches"
  | "records";

export interface Panel<T> {
  id: PanelId;
  eyebrow: string;
  title: string;
  status: DataStatus;
  badge?: string | null;
  data: T | null;
  note?: string | null;
  warnings: PageWarning[];
}

export interface IdentityBlock {
  player_id: number;
  name: string;
  full_name: string;
  href: string;
  season: string;
  role: string | null;
  age: number | null;
  nationality: string | null;
  number: number | null;
  status: string;
  injured: boolean;
  loan: {
    club: string | null;
    since: string | null;
    end_date: string | null;
  } | null;
  side: string | null;
  preferred_foot: KnownValue<string>;
}

export interface ClubHistoryRow {
  season: number | null;
  team_name: string | null;
  competition: string | null;
  appearances: number | null;
  starts: number | null;
  minutes: number | null;
}

export interface RoleInferenceModel {
  display_role: DisplayRole;
  role: PlayerRole;
  career_role: CareerRole;
  club_history: ClubHistoryRow[];
  tactical_notes: TacticalNote[];
  href: string;
}

export interface PositionPanel {
  display_role: DisplayRole;
  role: PlayerRole;
  career_role: CareerRole;
  history_status: "observed" | "partial" | "no_role_evidence";
  club_history: ClubHistoryRow[];
  tactical_notes: TacticalNote[];
}

export interface PlayingTimePanel {
  playing_time: PlayerPlayingTime;
}

export interface PerformanceTile {
  key: string;
  label: string;
  value: number | null;
  note: string;
}

export interface TableColumn {
  key: keyof SquadStat | "competition" | "team_name";
  label: string;
  format?: "int" | "decimal" | "percent";
}

export interface PerformancePanel {
  tiles: PerformanceTile[];
  provider_columns: TableColumn[];
  detail_columns: TableColumn[];
  stats: SquadStat[];
  position_stats: SquadPositionStat[];
  stats_coverage: string;
  stats_note: string;
  position_stats_coverage: string;
  position_stats_note: string;
}

export interface ProfileSummary {
  season: string;
  league: string;
  league_label: string;
  role_label: string | null;
  minutes: number;
  appearances: number | null;
  rating: number | null;
  rating_percentile: number | null;
  cohort_basis: string | null;
  cohort_n: number | null;
}

export interface ProfilePanelData {
  tier: "extended" | "standard";
  current_squad: boolean;
  summary: ProfileSummary;
  rose: RoseBlock;
  rose_catalogue: RoseCatalogue;
}

export interface AvailabilityBlock {
  status: string;
  reason: string | null;
  reason_category: string | null;
  expected_return: string | null;
  confidence: string;
  source_id: string | null;
  source_title: string | null;
  source_url: string | null;
  verified_at: string | null;
  note: string | null;
  in_squad: boolean | null;
}

export interface AvailabilityPanelData {
  availability: AvailabilityBlock;
}

export interface RecentMatch {
  fixture_id: number | string;
  date: string;
  competition: string;
  opponent: string;
  venue: "H" | "A" | null;
  score_for: number | null;
  score_against: number | null;
  result: "W" | "D" | "L" | null;
  minutes: number | null;
  rating: number | null;
  goals: number | null;
  assists: number | null;
}

export interface PlayerPageDocument {
  schema_version: "1.1.0";
  player_id: number;
  season: string;
  generated_at: string;
  identity: IdentityBlock;
  panel_order: PanelId[];
  panels: {
    profile: Panel<ProfilePanelData>;
    availability: Panel<AvailabilityPanelData>;
    position: Panel<PositionPanel>;
    playing_time: Panel<PlayingTimePanel>;
    performance: Panel<PerformancePanel>;
    recent_matches: Panel<RecentMatch[]>;
    records: Panel<SquadStat[]>;
  };
  warnings: PageWarning[];
}
