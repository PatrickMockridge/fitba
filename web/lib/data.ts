import fs from "node:fs";
import path from "node:path";

import type { PlayerPageDocument } from "@/lib/player-page";
import type { RoseBlock, RoseCatalogue } from "@/lib/rose";

const DATA_DIR = path.join(process.cwd(), "data", "generated");

export interface TableRow {
  position: number;
  team_id: string;
  team_name: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  raw_points: number;
  deduction: number;
  points: number;
  form: string;
  season: string;
  competition_id: string;
  competition_name: string;
  updated_at: string;
}

export interface Cutoff {
  after_position: number;
  kind: "europe" | "split" | "promotion" | "playoff" | "pyramid" | "relegation" | string;
  label: string;
  note?: string;
}

export interface TableFile {
  competition_id: string;
  competition_name: string;
  short_name: string;
  tier: number;
  season: string;
  qualification_note?: string | null;
  cutoffs?: Cutoff[];
  rows: TableRow[];
}

export interface ClubResult {
  match_id: string;
  date: string;
  competition_id: string;
  opponent_id: string;
  opponent_name: string;
  venue: "H" | "A";
  goals_for: number;
  goals_against: number;
  result: "W" | "D" | "L";
  result_label?: string;
  outcome?: "W" | "D" | "L";
  shootout_result?: string | null;
  decided_by?: string;
}

export interface ClubHistory {
  season: string;
  position: number;
  played: number;
  points: number;
  gd: number;
  form: string;
}

export interface ClubFixture {
  match_id: string;
  competition_id: string;
  competition_name: string;
  stage?: string | null;
  date: string;
  kickoff?: string | null;
  opponent_id: string;
  opponent_name: string;
  venue: "H" | "A" | "N";
  neutral?: boolean;
  status: string;
  goals_for?: number;
  goals_against?: number;
  result?: "W" | "D" | "L";
  result_label?: string;
  outcome?: "W" | "D" | "L";
  shootout_result?: string | null;
  decided_by?: string;
}

export interface ClubCompetition {
  id: string;
  name: string;
  short_name: string;
  status: string;
  stage?: string | null;
  entry_round?: string | null;
  entry_date?: string | null;
  note?: string | null;
  next_fixture: ClubFixture | null;
  source?: string | null;
  verified_at?: string | null;
}

export interface NewsArticle {
  article_id: string;
  title: string;
  category: string;
  category_slug: string;
  published_date: string | null;
  url: string;
  source: string;
  player_mentions?: PlayerMention[];
}

export interface CupFixture {
  match_id: string;
  round: string;
  round_order: number;
  group?: string | null;
  date: string;
  kickoff?: string | null;
  home_team_id: string;
  home_team_name: string;
  away_team_id: string;
  away_team_name: string;
  home_goals: number | null;
  away_goals: number | null;
  home_penalties: number | null;
  away_penalties: number | null;
  status: string;
  winner_team_id?: string | null;
  extra_time?: boolean;
  venue?: string | null;
}

export interface CupGroupRow {
  group: string;
  team_id: string;
  team_name: string;
  played: number;
  won: number;
  shootout_won: number;
  shootout_lost: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
  position: number;
}

export interface CupGroup {
  id: string;
  rows: CupGroupRow[];
}

export interface CupRound {
  name: string;
  order: number;
  fixtures: CupFixture[];
  note?: string;
  official_ties?: number | null;
  official_date?: string | null;
  covered?: boolean;
}

export interface CupSource {
  id: string;
  name: string;
  url: string;
  verified_at?: string | null;
}

export interface LeagueCupFile {
  competition_id: string;
  name: string;
  short_name: string;
  kind: "cup";
  season: string;
  format: Record<string, unknown>;
  status: {
    phase: string;
    next_fixtures: CupFixture[];
    coverage_note?: string;
  };
  groups: CupGroup[];
  group_winners: CupGroupRow[];
  best_runners_up: CupGroupRow[];
  byes: Array<{ team_id: string; team_name: string }>;
  qualifiers: {
    count: number;
    group_winners: CupGroupRow[];
    best_runners_up: CupGroupRow[];
    byes: Array<{ team_id: string; team_name: string }>;
  };
  rounds: CupRound[];
  fixtures: CupFixture[];
  validation?: {
    qualifiers_match_r16: boolean;
    qualifier_count: number;
    mismatch: string[];
  };
  source: CupSource;
}

export interface ScottishCupFile {
  competition_id: string;
  name: string;
  short_name: string;
  kind: "cup";
  season: string;
  format: Record<string, unknown>;
  coverage: {
    official_ties: number;
    licensed_ties: number;
    rounds_present: string[];
    rounds_missing: string[];
    note: string;
    status: "partial" | "full";
  };
  status: { phase: string; next_fixtures: CupFixture[] };
  rounds: CupRound[];
  fixtures: CupFixture[];
  aberdeen: {
    entry_round?: string | null;
    entry_date?: string | null;
    status: string;
    note?: string | null;
  };
  source: CupSource;
}

export interface CompetitionIndexEntry {
  id: string;
  name: string;
  short_name: string;
  kind: "league" | "cup";
  tier?: number;
  season: string;
  status: string;
  leader?: TableRow | null;
  stage?: string | null;
  next_fixture?: CupFixture | null;
  aberdeen_note?: string | null;
  link: string;
  coverage: string;
  aberdeen_involved: boolean;
}

export interface EuropeanCompetitionIndex {
  id: string;
  name: string;
  short_name: string;
  stage?: string | null;
  next_fixture?: CupFixture | null;
  source?: string | null;
  verified_at?: string | null;
  link?: string | null;
}

export interface CompetitionIndex {
  season: string;
  competitions: CompetitionIndexEntry[];
  europe?: {
    season: string;
    in_europe: boolean;
    note?: string | null;
    competitions: EuropeanCompetitionIndex[];
  };
}

export type TransferPositionSource =
  | "curated"
  | "squad"
  | "api_player_stats"
  | "career_role"
  | "unknown";

export type TransferPositionUnknownReason =
  | "no_allowed_source"
  | "player_not_found"
  | "youth_no_profile"
  | "conflicting_sources"
  | "budget"
  | "historical_scope";

export interface TransferFeeEstimate {
  basis: "disclosed" | "reported" | "free" | "loan" | "modelled" | "unknown" | string;
  currency: string;
  fee_low_gbp: number | null;
  fee_high_gbp: number | null;
  market_value_low_gbp: number | null;
  market_value_high_gbp: number | null;
  confidence: string;
  method: string;
  reported_currency?: string | null;
  reported_note?: string | null;
  source_urls: string[];
  note: string;
}

export interface SellOnClause {
  clause_id: string;
  transfer_id: string;
  player_key: string;
  player_name: string;
  buyer_club_id: string;
  buyer_club_name: string;
  sale_date: string;
  sell_on_pct: number | null;
  basis: "profit" | "gross_fee" | "unknown" | string;
  confidence: "confirmed" | "reported" | "unknown" | string;
  source_urls: string[];
  verification_aid: string;
  verified_at: string;
  notes: string;
  fee_display?: string | null;
  fee_estimate?: TransferFeeEstimate | null;
}

export interface TransferValuationSummary {
  currency: string;
  fee_low_gbp: number | null;
  fee_high_gbp: number | null;
  spend_low_gbp: number;
  spend_high_gbp: number;
  income_low_gbp: number;
  income_high_gbp: number;
  confidence: string;
  counts: Record<string, number>;
  note: string;
  calibration_factor?: number;
  anchor_count?: number;
}

export interface TransferRecord {
  transfer_id: string;
  player_key: string;
  player_name: string;
  position?: string | null;
  position_source?: TransferPositionSource | null;
  position_source_season?: string | null;
  position_unknown_reason?: TransferPositionUnknownReason | null;
  nationality?: string | null;
  direction: "in" | "out";
  transfer_kind: "permanent" | "loan" | "free" | string;
  from_club_id: string;
  from_club_name: string;
  to_club_id: string;
  to_club_name: string;
  date_effective: string;
  date_announced: string;
  season: string;
  window: "summer" | "winter" | "other" | string;
  fee_status: string;
  fee_amount?: number | null;
  fee_currency?: string | null;
  fee_display: string;
  fee_estimate?: TransferFeeEstimate | null;
  loan_end_date?: string | null;
  recall_clause?: boolean | null;
  obligation_to_buy?: boolean | null;
  option_to_buy?: boolean | null;
  verification_status: "confirmed" | "curated" | string;
  source_urls: string[];
  verified_at?: string | null;
  notes?: string | null;
  player_href?: string | null;
}

export interface TransferWindow {
  key: string;
  season: string;
  window: string;
  label: string;
  coverage: "audited" | "curated_partial" | string;
  state: "closed" | "open" | "upcoming" | string;
  era_context: "era" | "pre_era" | string;
  arrivals: number;
  departures: number;
  permanent_in: number;
  permanent_out: number;
  loans_in: number;
  loans_out: number;
  free_in: number;
  free_out: number;
  disclosed_spend: number;
  disclosed_income: number;
  net_spend: number;
  disclosed_count: number;
  undisclosed_count: number;
  inferred_net_low_gbp?: number | null;
  inferred_net_high_gbp?: number | null;
  valuation_confidence?: string | null;
  valuation_counts?: Record<string, number> | null;
}

export interface TransfersFile {
  club_id: string;
  name: string;
  season: string;
  seasons: string[];
  windows: TransferWindow[];
  window_groups: {
    recent: string[];
    further: string[];
    out_of_window: string[];
    upcoming?: string[];
  };
  transfers: TransferRecord[];
  loans_out: TransferRecord[];
  loans_in: TransferRecord[];
  loan_scope?: {
    season: string;
    official_list: { out_count: number; in_count: number };
    register_current: { out_count: number; in_count: number };
    register_all_time: { out_count: number; in_count: number };
    reconciliation: {
      matched_out: number;
      register_only_out: Array<{ player_name: string | null; club: string | null }>;
      official_only_out: Array<{ player_name: string | null; club: string | null }>;
    };
  };
  summary: {
    total: number;
    confirmed: number;
    curated: number;
    players: number;
    seasons_covered: number;
    windows_covered: number;
    period: string | null;
  };
  coverage: {
    status: string;
    audited_from?: string;
    historical_from?: string;
    note: string;
  };
  valuation?: TransferValuationSummary | null;
  plausibility?: { withheld: number; note: string } | null;
  sell_on_clauses: SellOnClause[];
  sell_on_summary: {
    total: number;
    confirmed: number;
    reported: number;
    percentage_known: number;
    percentage_unknown: number;
    note: string;
  };
  sources: string[];
  notes: string;
}

export type TransferSeniority = "established" | "fringe" | "youth" | "unclassified";
export type TransferGapStatus = "open" | "accepted" | "resolved";
export type TransferVerificationAid = "manual_third_party" | "allowed_source" | "none";

export interface TransferAuditItem {
  player_key: string;
  player_name?: string | null;
  seniority: TransferSeniority;
  reason: string;
  season?: string | null;
}

export interface TransferAuditGap {
  player_key?: string | null;
  player_name?: string | null;
  direction: "in" | "out" | string;
  season?: string | null;
  window?: string | null;
  seniority: Exclude<TransferSeniority, "unclassified">;
  status: TransferGapStatus;
  reason?: string | null;
  verification_aid: TransferVerificationAid;
  checked_at?: string | null;
  transfer_id?: string | null;
}

export interface TransferAudit {
  generated_at: string;
  audit_start: string;
  status: "ok" | "unavailable";
  snapshot_at?: string | null;
  summary: {
    needs_review: Record<TransferSeniority, number>;
    gaps: Record<TransferGapStatus, number>;
    positions: { specified: number; unknown: number };
  };
  current_squad_arrivals: TransferAuditItem[];
  prior_departures: TransferAuditItem[];
  candidate_review: { key: string; season: string; window: string; count: number }[];
  windows: {
    key: string;
    season: string;
    window: string;
    arrivals: number;
    departures: number;
    position_unknown: number;
  }[];
  gaps: TransferAuditGap[];
}

export interface FormerDeparture {
  transfer_id: string;
  date: string;
  season: string;
  window: string;
  kind: string;
  fee_status: string;
  fee_amount: number | null;
  fee_currency: string | null;
  fee_display: string;
  fee_estimate?: TransferFeeEstimate | null;
  to_club_id?: string | null;
  to_club_name: string | null;
  to_market: string;
  to_country: string | null;
  is_scottish_club: boolean | null;
  is_rival: boolean;
  rival_name: string | null;
  verification_status: string;
  source_urls: string[];
}

export interface FormerCurrent {
  club_id?: string | number | null;
  club_name: string | null;
  parent_club_name?: string | null;
  league: string | null;
  country: string | null;
  league_tier: number | null;
  status: "at_club" | "on_loan" | "free_agent" | "retired" | "unknown" | string;
  source: string;
  coverage: "current" | "historical" | "unknown" | string;
  market?: string;
  is_scottish_club?: boolean | null;
  is_rival?: boolean;
  rival_name?: string | null;
  rival_current?: boolean;
  as_of?: string | null;
}

export interface FormerSeasonRow {
  season: string;
  team_name: string;
  competition: string;
  country: string | null;
  league_tier: number | null;
  appearances: number | null;
  starts: number | null;
  minutes: number | null;
  goals: number | null;
  assists: number | null;
  rating: number | null;
  goals_p90: number | null;
  assists_p90: number | null;
  source: string;
}

export interface FormerPlayer {
  player_key: string;
  player_id: number | null;
  identity_status: string;
  alias_keys: string[];
  name: string;
  position: string | null;
  nationality: string | null;
  birth_date: string | null;
  age_at_exit: number | null;
  href: string;
  transfer_href: string | null;
  departure: FormerDeparture;
  aberdeen: {
    coverage: string;
    first_season: string | null;
    last_season: string | null;
    seasons: string[];
    squad_selections: number | null;
    appearances: number | null;
    starts: number | null;
    sub_apps: number | null;
    minutes: number | null;
    goals: number | null;
    assists: number | null;
    rating: number | null;
    rating_note: string;
    final_season: Record<string, unknown>;
    history_from: string;
    tenure_coverage: string;
    first_appearance_covered: string | null;
    age_at_first_appearance_covered: number | null;
    developed_here: string;
    developed_basis: string;
  };
  post_career: {
    status: string;
    coverage_note: string;
    seasons_expected: number;
    seasons_with_data: number;
    first_season: string | null;
    last_season: string | null;
    totals: {
      seasons_expected: number;
      seasons_with_data: number;
      appearances: number | null;
      starts: number | null;
      minutes: number | null;
      goals: number | null;
      assists: number | null;
    };
    clubs: { club: string; minutes: number }[];
    countries: { country: string; minutes: number }[];
    current: FormerCurrent;
    top_flight: boolean | null;
    top_flight_abroad: boolean | null;
    at_rival: boolean;
    rival_current: boolean;
    rival_spells: {
      club: string;
      from_season: string;
      to_season: string;
      current: boolean;
    }[];
  };
  sell_on_clause_id: string | null;
}

export interface FormerReceipt {
  status: string;
  receipt_gbp: number | null;
  gross_fee_gbp: number | null;
  original_fee_gbp: number | null;
  profit_gbp: number | null;
  currency: string;
  method: string | null;
  inputs: Record<string, unknown>;
  missing_inputs: string[];
  confidence: string | null;
}

export interface FormerSellOnClause {
  clause_id: string;
  player_key: string;
  player_name: string;
  buyer_club_name: string;
  sale_date: string;
  sell_on_pct: number | null;
  basis: string;
  confidence: string;
  source_urls: string[];
  notes?: string | null;
  event: {
    date: string;
    from_club_name: string | null;
    to_club_name: string | null;
    kind: string;
    fee_status: string;
    fee_display: string | null;
    source_urls: string[];
  } | null;
  event_status: string;
  receipt: FormerReceipt;
}

export interface FormerPlayersFile {
  schema_version: string;
  club_id: string;
  name: string;
  season: string;
  generated_at: string;
  state: "available" | "partial" | "stale" | "unavailable" | string;
  served_generated_at: string | null;
  definition: Record<string, unknown>;
  coverage: {
    status: string;
    as_of: string;
    register_from: string;
    post_career_source: string;
    post_career_updated_at: string | null;
    backfill: Record<string, unknown>;
    counts: Record<string, number>;
    gaps: { player_key: string; season?: string; reason: string }[];
    note: string;
  };
  summary: Record<string, number | Record<string, number> | null>;
  players: FormerPlayer[];
  sell_on_watch: {
    clauses: FormerSellOnClause[];
    summary: Record<string, number | string | null>;
  };
  development_scorecard: {
    definitions: Record<string, number | string>;
    cohorts: Record<string, Record<string, number | null>>;
    by_exit_season: Record<string, number | string>[];
    vs_aberdeen: Record<string, number>;
    note: string;
  };
  sources: { id: string; name: string; url: string | null; verified_at: string | null; note: string }[];
  notes: string;
}

export interface FormerPlayerSeasons {
  coverage: {
    status: string;
    expected_seasons: string[];
    present_seasons: string[];
    missing_seasons: string[];
  };
  aberdeen_by_season: {
    season: string;
    squad_selections: number;
    appearances: number;
    starts: number;
    sub_apps: number;
    minutes: number;
    goals: number | null;
    assists: number | null;
    rating: number | null;
  }[];
  post_seasons: FormerSeasonRow[];
  transfer_chain: {
    date: string;
    from_club_name: string | null;
    to_club_name: string | null;
    kind: string;
  }[];
  vs_aberdeen: {
    coverage: string;
    appearances: number;
    starts: number;
    minutes: number;
    goals: number | null;
    assists: number | null;
    note: string;
  };
}

export interface FormerSeasonsFile {
  schema_version: string;
  generated_at: string;
  season: string;
  club_id: string;
  state: string;
  seasons: Record<string, FormerPlayerSeasons>;
  coverage: {
    players_with_detail: number;
    players_without_detail: number;
    note: string;
  };
}

export type RumourStatus = "active" | "denied" | "confirmed" | "stale";
export type RumourConfidence = "low" | "medium" | "high";

export interface Rumour {
  rumour_id: string;
  player_key: string | null;
  linked_player_key: string | null;
  player_name: string;
  linked_club: string;
  direction: "in" | "out";
  current_club: string | null;
  position: string | null;
  age: number | null;
  league: string | null;
  value_band: string;
  claim: string;
  status: RumourStatus;
  confidence: RumourConfidence;
  source_urls: string[];
  source_types: string[];
  first_seen: string | null;
  last_seen: string | null;
  verified_at: string | null;
  linked_transfer_id: string | null;
  analysis_tags: string[];
  engagement: null;
  player_href?: string | null;
  former_href?: string | null;
  affiliation?: string;
  affiliation_source?: string;
  is_target?: boolean;
  is_return_link?: boolean;
  player_mentions?: PlayerMention[];
}

export interface RumourOpinion {
  opinion_id: string;
  title: string;
  stance: string;
  body: string;
  evidence: string[];
  published: string | null;
  label: string;
  player_mentions?: PlayerMention[];
}

export interface RumoursFile {
  club_id: string;
  name: string;
  season: string;
  generated_at: string;
  rumours: Rumour[];
  opinions: RumourOpinion[];
  summary: {
    total: number;
    by_status: Record<string, number>;
    by_confidence: Record<string, number>;
    by_source_type: Record<string, number>;
    by_direction: Record<string, number>;
  };
  coverage: { status: string; note: string };
  lanes?: Record<string, { count: number; rumour_ids: string[] }>;
  former_player_mentions?: Rumour[];
  notes: string;
}

export interface RumourProfileSignal {
  rumour_id: string;
  player_name: string;
  position: string | null;
  age: number | null;
  league: string | null;
  value_band: string | null;
  confidence: string;
  weight: number;
  player_href?: string | null;
}

export interface RumourProfile {
  club_id: string;
  generated_at: string;
  sample_size: number;
  basis?: string;
  candidate_rows?: number;
  excluded?: Record<string, number>;
  return_links?: {
    rumour_id: string;
    player_name: string;
    claim: string;
    player_href?: string | null;
    former_href?: string | null;
  }[];
  weighted_total: number;
  low_confidence: boolean;
  weights: {
    confidence: Record<string, number>;
    recency_half_life_days: number;
    recency_floor: number;
  };
  buckets: {
    position: Record<string, number>;
    age_band: Record<string, number>;
    league: Record<string, number>;
    value_band: Record<string, number>;
  };
  narrative: string;
  signals: RumourProfileSignal[];
  note: string;
}

export interface SentimentSummary {
  count: number;
  mean: number | null;
  median: number | null;
  positive_share: number | null;
  neutral_share: number | null;
  negative_share: number | null;
}

export interface ForumTopic {
  title: string;
  url: string;
  published_at: string | null;
  latest_post: string | null;
  sampled_posts: number;
  player_mentions?: PlayerMention[];
}

export interface ForumSignal {
  player_name: string;
  player_key: string | null;
  position: string | null;
  position_group: string | null;
  nationality: string | null;
  age: number | null;
  mentions: number;
  topic_count: number;
  credibility: string;
  affiliation?: string;
  affiliation_source?: string;
  former_href?: string | null;
  current_club?: string | null;
  current_league?: string | null;
  at_rival?: boolean;
  rival_club?: string | null;
  cross_references: {
    confirmed_transfer: boolean;
    historic_transfer?: boolean;
    press_rumour: boolean;
    club_output: boolean;
  };
  player_href?: string | null;
}

export interface ForumSignalFile {
  source: {
    id: string;
    name: string;
    url: string | null;
    rss: string | null;
    content_signal: string | null;
  };
  generated_at: string;
  sampled_at?: string | null;
  coverage: {
    topics_sampled: number;
    posts_sampled: number;
    first_page_only: boolean;
    raw_posts_published: boolean;
    note: string;
  };
  topics: ForumTopic[];
  signals: ForumSignal[];
  profile: {
    sample_size: number;
    total_signals?: number;
    external_sample_size?: number;
    position_mix: Record<string, number>;
    age_mix: Record<string, number>;
    source_mix: Record<string, number>;
    affiliation_mix?: Record<string, number>;
    excluded_counts?: Record<string, number>;
    lanes?: Record<string, { count: number; players: string[] }>;
    former_player_profile?: {
      sample_size: number;
      mentions: number;
      players: string[];
    };
    low_confidence: boolean;
    note: string;
  };
  sentiment: {
    forum: SentimentSummary;
    press: SentimentSummary;
    club: SentimentSummary;
    note: string;
  };
  notes: string;
}

export interface PlayerMention {
  name: string;
  href: string;
}

export interface SquadStat {
  scope: "club" | "loan" | "other" | string;
  competition: string;
  team_name: string;
  season: number;
  appearances: number | null;
  starts: number | null;
  minutes: number | null;
  goals: number | null;
  assists: number | null;
  yellow_cards: number | null;
  red_cards: number | null;
  rating: number | null;
  shots_total: number | null;
  shots_on: number | null;
  passes_total: number | null;
  passes_key: number | null;
  pass_accuracy: number | null;
  saves: number | null;
  conceded: number | null;
  tackles: number | null;
  blocks: number | null;
  interceptions: number | null;
  duels_total: number | null;
  duels_won: number | null;
  dribbles_attempts: number | null;
  dribbles_success: number | null;
  fouls_drawn: number | null;
  fouls_committed: number | null;
  penalty_won: number | null;
  penalty_committed: number | null;
  penalty_scored: number | null;
  penalty_missed: number | null;
  penalty_saved: number | null;
}

export interface SquadTotals {
  appearances: number;
  starts: number;
  minutes: number;
  goals: number;
  assists: number;
  yellow_cards: number;
  red_cards: number;
  saves: number;
  tackles: number;
  blocks: number;
  interceptions: number;
  duels_won: number;
  fouls_committed: number;
  penalty_scored: number;
  penalty_saved: number;
  shots_total: number;
  shots_on: number;
  passes_key: number;
  dribbles_success: number;
  rating: number | null;
}

export interface SquadPositionStat {
  player_id: number;
  player_key: string;
  competition: string;
  matches: number;
  minutes_on_pitch: number;
  conceded_on_pitch: number;
  clean_sheets: number;
  own_goals: number;
}

export interface SquadPositionTotals {
  matches: number;
  minutes_on_pitch: number;
  conceded_on_pitch: number;
  clean_sheets: number;
  own_goals: number;
}

export interface AttributeSource {
  id: string;
  tier: number;
  url: string | null;
  revision: string | null;
  verified_at: string | null;
  confidence: string;
  derivation: string;
}

export interface PlayerAttribute {
  value: string | null;
  status: "known" | "unknown" | "conflict" | string;
  unknown_reason: string | null;
  source: AttributeSource | null;
  conflict_state: "none" | "resolved_by_precedence" | "unresolved" | "override_applied" | string;
  conflict_sources: Array<{ source_id: string; source_url: string | null }>;
}

export interface PlayerAttributes {
  preferred_foot: PlayerAttribute;
  coverage: "known" | "unknown" | "conflict" | string;
}

export interface RoleHistoryRow {
  code: string;
  label: string;
  family: string;
  starts: number;
  minutes: number;
}

export interface PlayerRole {
  primary: string | null;
  code: string | null;
  family: string | null;
  side: "left" | "right" | "central" | null;
  status: "observed" | "partial" | "unknown" | string;
  starts_with_role: number;
  starts_total: number;
  coverage: string;
  roles: RoleHistoryRow[];
  slots?: CareerSlotShare[];
  fm_label?: string;
  broad_groups?: string[];
  sides?: string[];
  primary_slot?: CareerSlotShare | null;
  unknown_reason: string | null;
  source: {
    id: string;
    method: string;
    fixtures_covered: number;
    starts_with_role: number;
  } | null;
}

export interface PlayingTimeCompetition {
  competition: string;
  starts: number;
  sub_apps: number;
  minutes: number;
  minutes_started: number;
  minutes_as_sub: number;
}

export interface CareerRoleShare {
  code?: string;
  label: string;
  family: string;
  family_label?: string;
  starts: number;
  weighted_starts?: number;
  share: number;
}

export interface CareerRoleDominant {
  code: string;
  label: string;
  family: string;
  family_label: string;
  side: "left" | "right" | "central" | null;
  starts: number;
  weighted_starts: number;
  share: number;
  provisional: boolean;
}

export interface CareerSlotShare {
  slot: string;
  label: string;
  fm: string;
  side: "left" | "centre" | "right" | null;
  groups: string[];
  starts: number;
  weighted_starts?: number;
  share: number;
  tier: "primary" | "secondary" | "stretch" | "other" | string;
}

export interface CareerPrimarySlot {
  slot: string;
  label: string;
  fm: string;
  side: "left" | "centre" | "right" | null;
  groups: string[];
  code: string | null;
  role_label: string | null;
  family: string | null;
  starts: number;
  weighted_starts: number;
  share: number;
}

export interface CareerSeasonFamily {
  family: string;
  label: string;
  starts: number;
  share: number;
}

export interface CareerSeasonSlot {
  slot: string;
  label: string;
  fm: string;
  side: "left" | "centre" | "right" | null;
  groups: string[];
  starts: number;
  share: number;
}

export interface CareerSeasonScope {
  scope: string;
  starts: number;
  share: number;
}

export interface CareerSeason {
  season: string;
  season_year: number | null;
  starts_with_role: number;
  families: CareerSeasonFamily[];
  slots: CareerSeasonSlot[];
  scopes: CareerSeasonScope[];
}

export interface CareerScope {
  scope: string;
  label: string;
  starts: number;
  share: number;
}

export interface CareerHistoryRow {
  season: string;
  team_id: number | null;
  team_name: string | null;
  scope: string;
  competition: string | null;
  role_code: string;
  role_label: string;
  role_family: string;
  starts: number;
  share: number;
}

export interface CareerRole {
  status: "observed" | "low_evidence" | "mixed" | "unknown" | "unavailable" | string;
  dominant: CareerRoleDominant | null;
  secondary: CareerRoleShare[];
  top_families: CareerRoleShare[];
  family_shares: CareerRoleShare[];
  role_shares: CareerRoleShare[];
  primary_slot: CareerPrimarySlot | null;
  slot_definitions: Array<{
    slot: string;
    label: string;
    fm: string;
    side: "left" | "centre" | "right" | null;
    groups: string[];
    order: number;
  }>;
  slots: CareerSlotShare[];
  eligibility: CareerSlotShare[];
  secondary_slots: CareerSlotShare[];
  stretch_slots: CareerSlotShare[];
  broad_groups: string[];
  sides: string[];
  fm_label: string;
  starts_total: number;
  starts_with_role: number;
  coverage: string;
  seasons_with_role: number;
  unknown_reason: string | null;
  seasons: CareerSeason[];
  scopes: CareerScope[];
  history: CareerHistoryRow[];
  policy: Record<string, unknown>;
  policy_version: string;
  note: string;
}

export interface DisplayRole {
  code: string | null;
  label: string | null;
  family: string | null;
  family_label: string | null;
  side: "left" | "right" | "central" | null;
  source:
    | "career"
    | "aberdeen_override"
    | "current_season"
    | "career_low_evidence"
    | "none"
    | string;
  reason: string;
  starts: number;
  share: number;
  career_dominant: CareerRoleDominant | null;
  conditions?: Record<string, unknown>;
}

export interface TacticalNote {
  note_type: string;
  note: string;
  source: string;
  verified_at: string;
}

export interface CareerMeta {
  generated_at: string | null;
  status?: string;
  policy_version: string | null;
  seasons: string[];
  players: number;
  pairs_total: number;
  pairs_complete: number;
  pairs_skipped: number;
  pairs_capped: number;
  pairs_error: number;
  pairs_budget: number;
  evidence_rows: number;
  starts_with_role: number;
  network_requests: number;
  budget: number | null;
  budget_exhausted: boolean;
  unknown_reasons: Record<string, number>;
  errors: string[];
  unknown_reason?: string;
}

export interface PlayerPlayingTime {
  starts: number;
  sub_apps: number;
  minutes: number;
  minutes_started: number;
  minutes_as_sub: number;
  coverage: "available" | "partial" | "unavailable" | "not_applicable" | string;
  by_competition: PlayingTimeCompetition[];
  note?: string;
}

export interface AttributesMeta {
  rows: number;
  known: number;
  conflicts: number;
  unknown: number;
  by_attribute: Record<string, Record<string, number>>;
  by_source: Record<string, number>;
  sources: Record<string, string>;
  note: string;
  ingested_at: string;
}

export interface SquadPlayer {
  player_id: number;
  player_key: string;
  href: string;
  name: string;
  full_name: string;
  firstname: string | null;
  lastname: string | null;
  age: number | null;
  number: number | null;
  position: string | null;
  position_group: string | null;
  nationality: string | null;
  injured: boolean;
  provider_flag?: boolean;
  availability?: {
    status?: string;
    confidence?: string;
    source_id?: string;
    source_url?: string | null;
    verified_at?: string | null;
    note?: string | null;
    stale?: boolean;
    conflict?: boolean;
  };
  status: "squad" | "loan_out" | "loan_in" | string;
  loan: {
    club: string | null;
    since: string | null;
    end_date: string | null;
  } | null;
  stats_coverage: "available" | "partial" | "unavailable" | string;
  stats_scope?: "all_competitions" | "loan" | string;
  output_missing_competitions?: string[];
  stats_note: string;
  roster_status: "official" | "official_loan" | "excluded_api" | "provider_fallback" | string;
  squad_member: boolean;
  exclusion_reason: string | null;
  official_order: number | null;
  official_section: string | null;
  official_href: string | null;
  official_position: string | null;
  official_number: number | null;
  official_only: boolean;
  roster_conflict: boolean;
  identity_source: string;
  stats: SquadStat[];
  totals: SquadTotals | null;
  league_totals?: SquadTotals | null;
  loan_totals?: SquadTotals | null;
  attributes: PlayerAttributes;
  role: PlayerRole;
  career_role: CareerRole;
  display_role: DisplayRole;
  tactical_notes: TacticalNote[];
  playing_time: PlayerPlayingTime;
  position_stats: SquadPositionStat[];
  position_totals: SquadPositionTotals | null;
  position_stats_coverage: string;
  position_stats_note: string;
  other_stats: SquadStat[];
}

export interface MatchRolesMeta {
  fixtures_total: number;
  fixtures_with_lineups: number;
  fixtures_with_grid: number;
  fixtures_with_players: number;
  starts_total: number;
  starts_with_role: number;
  players_with_starts: number;
  players_with_role: number;
  formations_seen: Record<string, number>;
  unmapped_formations: string[];
  formation_mismatches: Array<Record<string, unknown>>;
  slot_errors: Array<Record<string, unknown>>;
  coverage: "available" | "partial" | "unavailable" | string;
  role_coverage: "available" | "partial" | "unavailable" | string;
  note: string;
  ingested_at: string | null;
}

export interface SquadFile {
  club_id: string;
  name: string;
  season: string;
  generated_at: string;
  players: SquadPlayer[];
  excluded_players?: SquadPlayer[];
  loan_scope?: {
    season: string;
    official_list: { out_count: number; in_count: number };
    register_current: { out_count: number; in_count: number };
    register_all_time: { out_count: number; in_count: number };
    reconciliation: {
      matched_out: number;
      register_only_out: Array<{ player_name: string | null; club: string | null }>;
      official_only_out: Array<{ player_name: string | null; club: string | null }>;
    };
  };
  roster_meta?: {
    status: string;
    source_url: string | null;
    fetched_at: string | null;
    official_players?: number;
    matched?: number;
    official_only?: number;
    provider_only?: number;
    ambiguous?: number;
    loan_section?: number;
    excluded_api?: number;
    note?: string | null;
  };
  roster_only?: Array<{
    name: string | null;
    number: number | null;
    position: string | null;
    section: string | null;
    official_href: string | null;
    reason: string;
  }>;
  summary: {
    total_players: number;
    squad_size: number;
    official_squad_size?: number;
    official_players?: number;
    official_only?: number;
    excluded_api?: number;
    provider_only?: number;
    official_source?: string | null;
    official_fetched_at?: string | null;
    loans_out: number;
    loans_in: number;
    average_age: number | null;
    stats_unavailable: number;
    stats_partial: number;
    by_position: Record<string, number>;
    by_role_family: Record<string, number>;
    by_role_family_squad: Record<string, number>;
    by_primary_group: Record<string, number>;
    by_primary_group_squad: Record<string, number>;
    by_primary_side: Record<string, number>;
    by_status: Record<string, number>;
    position_stats_coverage: string;
    fixtures_covered: number;
    fixtures_total: number;
    own_goals_total: number;
    attributes_foot_known: number;
    attributes_unknown: number;
    attributes_conflicts: number;
    roles_observed: number;
    roles_partial: number;
    roles_unknown: number;
    role_coverage: string;
    formations_seen: Record<string, number>;
    formations_unmapped: string[];
    playing_time_available: number;
    playing_time_unavailable: number;
    career_roles_observed: number;
    career_roles_low_evidence: number;
    career_roles_mixed: number;
    career_roles_unknown: number;
    career_roles_unavailable: number;
    display_overrides: number;
  };
  role_meta: MatchRolesMeta;
  career_meta: CareerMeta;
  position_stats_meta: {
    fixtures_total: number;
    fixtures_covered: number;
    coverage: string;
    note: string;
    missing_fixtures: Array<Record<string, unknown>>;
    ingested_at: string | null;
  };
  attributes_meta: AttributesMeta;
  coverage: { status: string; note: string };
}

export interface ShapeFormation {
  formation: string;
  shape_family: string | null;
  cb_count: number | null;
  dm_count: number | null;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goals_against_per_match: number;
  saves_total: number | null;
  saves_per_match: number | null;
  cb_rating: number | null;
}

export interface ShapeMatchday {
  fixture_id: number;
  date: string;
  competition: string;
  opponent: string;
  formation: string | null;
  formation_shape: string | null;
  shape_family: string | null;
  cb_count: number | null;
  dm_count: number | null;
  goals_for: number | null;
  goals_against: number | null;
  result: "W" | "D" | "L" | string | null;
  saves: number | null;
  cb_rating: number | null;
}

export interface ReportedShapeSwitch {
  fixture_id: number;
  minute: number;
  from_shape: string;
  to_shape: string;
  source_url: string;
  confidence: string;
  note: string | null;
}

export interface TeamShapes {
  coverage: {
    status: string;
    fixtures_total: number;
    fixtures_with_shape: number;
    fixtures_with_saves: number;
    fixtures_with_cb_ratings: number;
    grid_covered: number;
    note: string;
  };
  formations: ShapeFormation[];
  matchday: ShapeMatchday[];
  reported_switches: ReportedShapeSwitch[];
}

export interface ClubFile {
  club_id: string;
  name: string;
  profile: {
    nickname?: string;
    stadium?: string;
    city?: string;
    founded?: number;
    colours?: { primary?: string; secondary?: string };
  };
  budget: {
    mode: string;
    transfer_fee_ceiling_gbp: number | null;
    wage_ceiling_weekly_gbp: number | null;
    age_band: [number, number];
    notes?: string;
  };
  squad_needs: Record<string, number>;
  style_intent: Record<string, number | string>;
  season: string;
  summary: TableRow | null;
  results: ClubResult[];
  fixtures: ClubFixture[];
  recent_results: ClubFixture[];
  competitions: ClubCompetition[];
  news: NewsArticle[];
  history: ClubHistory[];
  shapes: TeamShapes;
  coverage: string;
  notes: string;
}

export interface HistoryPillar {
  id: string;
  title: string;
  statement: string;
  evidence: string[];
}

export interface HistoryEra {
  id: string;
  label: string;
  chairman_person_id: string;
  chairman_name?: string | null;
  start: string;
  start_precision: string;
  first_season: string;
  short_description: string;
  pillars: HistoryPillar[];
  read: string;
  source_urls: string[];
  source_ids: string[];
  verified_at: string;
}

export interface HistoryManagerRecord {
  stint_id: string | null;
  person_id: string | null;
  name: string | null;
  interim: boolean;
  start: string;
  end: string | null;
  stint_start?: string;
  stint_end?: string | null;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  points: number;
  ppg: number | null;
  first_match?: string | null;
  last_match?: string | null;
  boundary_matches?: number;
  scope: string;
}

export interface HistoryStaffStint {
  stint_id: string;
  role: string;
  role_group: string;
  start: string;
  end: string | null;
  start_precision?: string;
  end_precision?: string | null;
  interim: boolean;
  reason_out: string | null;
  source_ids: string[];
  source_urls: string[];
  verified_at: string;
  notes?: string;
  record?: HistoryManagerRecord | null;
}

export interface HistoryPerson {
  person_id: string;
  name: string;
  stints: HistoryStaffStint[];
}

export interface HistoryHonour {
  honour_id: string;
  competition_id: string;
  competition: string;
  season: string;
  date: string | null;
  date_precision: string;
  opponent: string | null;
  score: string | null;
  after_extra_time: boolean;
  penalties: string | null;
  venue: string | null;
  manager_person_id: string | null;
  manager_name: string | null;
  era: "cormack" | "pre_cormack";
  source_ids: string[];
  source_urls: string[];
  verified_at: string;
  notes?: string | null;
}

export interface HistorySeasonRef {
  season: string;
  status: "completed" | "in_progress";
  href: string;
  competition_name?: string | null;
  headline: string;
  honour_ids: string[];
  manager_person_ids: string[];
  review_status: string;
}

export interface HistoryBackfill {
  status: string;
  fixtures_total: number;
  fixtures_with_lineups: number;
  lineup_coverage: number | null;
  rosters: number;
  team_stats: number;
  note: string;
}

export interface HistoryIndex {
  schema_version: string;
  era: HistoryEra;
  generated_at: string;
  coverage: {
    status: string;
    seasons_curated: number;
    completed_seasons: number;
    analytics: Record<string, string>;
    backfill: Record<string, HistoryBackfill>;
    transfer_coverage: { audited_from: string; historical_from: string };
    note: string;
  };
  heavy_defeats?: Array<{
    season: string;
    date: string;
    competition_name: string | null;
    opponent: string;
    goals_for: number;
    goals_against: number;
    fixture_id: number | null;
    href: string | null;
  }>;
  europe?: Array<{
    season: string;
    competition_name: string | null;
    exit_round: string | null;
    outcome: string | null;
    note: string | null;
  }>;
  scorecard: {
    seasons: number;
    best_position: number | null;
    worst_position: number | null;
    average_position: number | null;
    average_points: number | null;
    manager_count: number;
    honours_total: number;
    honours_by_competition: Record<string, number>;
    recruitment?: Record<string, unknown>;
    selection?: Record<string, unknown>;
    style?: Record<string, unknown>;
  };
  baseline: {
    from?: string;
    to?: string;
    count?: number;
    average_points?: number;
    best_position?: number;
    worst_position?: number;
    average_position?: number;
    seasons?: Array<Record<string, unknown>>;
    note?: string;
  };
  staff: HistoryPerson[];
  honours: HistoryHonour[];
  seasons: HistorySeasonRef[];
  sources: Array<{ id: string; url: string; verified_at: string }>;
  notes: string;
}

export interface HistoryCupRun {
  competition_id: string;
  competition_name?: string;
  exit_round?: string;
  stage_reached?: string;
  outcome: string;
  note?: string;
  source_ids?: string[];
  source_urls?: string[];
}

export interface HistoryRecruitment {
  season: string;
  coverage: string;
  arrivals: number;
  departures: number;
  permanent_in: number;
  permanent_out: number;
  loans_in: number;
  loans_out: number;
  free_in: number;
  free_out: number;
  disclosed_spend: number;
  disclosed_income: number;
  disclosed_net: number | null;
  disclosed_count: number;
  undisclosed_count: number;
  market_mix: Array<{ market: string; arrivals: number; share: number | null }>;
  market_unknown_count: number;
  age_coverage: number | null;
  median_age: number | null;
  average_age: number | null;
  age_bands: Record<string, number>;
  top_source_clubs: Array<{ club: string; arrivals: number }>;
  valuation?: TransferValuationSummary | null;
  note: string;
}

export interface HistoryStyle {
  matches: number;
  coverage: string;
  shots_for_pm?: number | null;
  shots_against_pm?: number | null;
  shots_on_target_for_pm?: number | null;
  shots_on_target_against_pm?: number | null;
  corners_for_pm?: number | null;
  corners_against_pm?: number | null;
  fouls_for_pm?: number | null;
  fouls_against_pm?: number | null;
  shot_accuracy?: number | null;
  goals_for_pm?: number | null;
  goals_against_pm?: number | null;
  possession_for_pm?: number | null;
  possession_against_pm?: number | null;
  possession_unknown_reason?: string;
  tactical_note?: string | null;
  era_average?: Record<string, unknown>;
  note?: string;
  missing_stats?: string[];
}

export interface HistorySelection {
  status: string;
  reason?: string;
  fixtures_total?: number;
  fixtures_with_lineups?: number;
  lineup_coverage?: number | null;
  formation_mix?: Array<{ formation: string; fixtures: number; share: number }>;
  players_used?: number;
  average_starter_age?: number | null;
  age_coverage?: number | null;
  u21_minutes_share?: number | null;
  minutes_by_age_band?: Record<
    string,
    { minutes: number; share: number | null }
  >;
  unknown_age_minutes?: number;
  top_by_starts?: Array<{
    player_id: number;
    player_name: string | null;
    starts: number;
    minutes: number;
    role_family: string | null;
    age: number | null;
  }>;
  debutants?: Array<{ player_id: number; player_name: string | null; date: string }>;
  debut_basis?: string;
  tactical_note?: string | null;
  note?: string;
}

export interface HistoryStaffChange {
  stint_id: string;
  person_id: string;
  name: string;
  role: string;
  role_group: string;
  date: string;
  change: "in" | "out";
  interim: boolean;
  reason_out: string | null;
  source_urls: string[];
}

export interface HistorySeasonDocument {
  schema_version: string;
  season: string;
  status: "completed" | "in_progress";
  as_of: string | null;
  reviewed_at: string;
  headline: string;
  expectations: Record<string, unknown>;
  managers: HistoryManagerRecord[];
  cup_runs: HistoryCupRun[];
  europe: HistoryCupRun[];
  honour_ids: string[];
  key_transfers: {
    arrivals?: string[];
    departures?: string[];
    note?: string;
  };
  recruitment: HistoryRecruitment;
  style: HistoryStyle;
  selection: HistorySelection;
  academy: {
    debuts: Array<Record<string, unknown>>;
    measured_new_players: Array<Record<string, unknown>>;
    debut_basis: string | null;
    note: string;
  };
  tactical: {
    shape_note: string | null;
    style_note: string | null;
    selection_note: string | null;
  };
  staff_changes: HistoryStaffChange[];
  review: {
    what_worked: string;
    what_did_not: string;
    trade_off: string;
    read: string;
    look_ahead: string;
    label: string;
  } | null;
  interim_read: string | null;
  coverage: {
    league_record: string;
    manager_scope: string;
    unattributed_matches: number;
    history: HistoryBackfill;
    transfers: string;
    note: string;
  };
  sources: Array<{ id: string; url: string; verified_at: string }>;
}

export interface MatchdaySource {
  id: string;
  name: string;
  url?: string | null;
  verified_at?: string | null;
}

export interface MatchdayTeam {
  club_id: string;
  api_team_id: number | null;
  name: string;
  short_name?: string | null;
}

export interface MatchdayFixture {
  match_id: string;
  competition_id: string;
  competition_name: string;
  stage?: string | null;
  season: string;
  date: string;
  kickoff?: string | null;
  home_team_id: string;
  home_team_name: string;
  away_team_id: string;
  away_team_name: string;
  venue: "H" | "A" | string;
  opponent_id: string;
  opponent_name: string;
  status: string;
  source_id?: string | null;
}

export interface FormMatch {
  match_id?: string | null;
  date: string;
  opponent_id?: string | null;
  opponent_name?: string | null;
  venue?: "H" | "A" | string | null;
  gf: number;
  ga: number;
  result: "W" | "D" | "L" | string | null;
  points: number;
  competition_name?: string | null;
}

export interface FormRecord {
  played: number;
  won: number;
  drawn: number;
  lost: number;
  points: number;
  ppg: number | null;
  gf: number;
  ga: number;
  gd: number;
  gf_pg: number | null;
  ga_pg: number | null;
  gd_pg: number | null;
  shots_for_pm?: number | null;
  shots_against_pm?: number | null;
  shot_share?: number | null;
  [key: string]: unknown;
}

export interface FormBlock {
  basis: string;
  sample: Record<string, unknown>;
  matches: FormMatch[];
  form: string;
  recent: FormRecord;
  form_points: number;
  season_record: FormRecord;
  home: FormRecord;
  away: FormRecord;
  coverage: string;
  note: string;
}

export interface MatchdayStrength {
  status: string;
  team_id: string;
  team_name?: string | null;
  competition_id?: string | null;
  competition_name?: string | null;
  tier?: number | null;
  position?: number | null;
  played?: number | null;
  points?: number | null;
  ppg?: number | null;
  gf?: number | null;
  ga?: number | null;
  gd?: number | null;
  gf_pg?: number | null;
  ga_pg?: number | null;
  gd_pg?: number | null;
  form?: string | null;
  shots_for_pm?: number | null;
  shots_against_pm?: number | null;
  shot_share?: number | null;
  percentiles?: Record<string, number | null>;
  ranks?: Record<string, number | null>;
  league_size?: number | null;
  coverage?: string | null;
  sample_note?: string | null;
  reason?: string | null;
}

export interface StyleProfile {
  matches: number;
  coverage: string;
  venue: "H" | "A" | "all" | string;
  season?: string | null;
  shots_for_pm?: number | null;
  shots_against_pm?: number | null;
  shots_on_target_for_pm?: number | null;
  shots_on_target_against_pm?: number | null;
  corners_for_pm?: number | null;
  corners_against_pm?: number | null;
  fouls_for_pm?: number | null;
  goals_for_pm?: number | null;
  goals_against_pm?: number | null;
  shot_share?: number | null;
  conversion?: number | null;
  shot_accuracy?: number | null;
  percentiles?: Record<string, number | null>;
  possession_for_pm?: number | null;
  possession_against_pm?: number | null;
  possession_unknown_reason?: string | null;
  missing_stats?: string[];
  note?: string | null;
  reason?: string | null;
}

export interface StyleLean {
  approach: "attack" | "balanced" | "sit_deep_counter" | "unknown" | string;
  label: string;
  confidence: "high" | "medium" | "low" | "unknown" | string;
  approach_index?: number | null;
  venue_index?: number | null;
  overall_index?: number | null;
  shot_share?: number | null;
  venue_matches: number;
  venue_used: boolean;
  evidence: string[];
  basis: string;
  interpretation: string;
  missing_metrics?: string[];
  reason?: string | null;
  note?: string | null;
}

export interface StylePair {
  overall: StyleProfile;
  venue: StyleProfile;
  lean: StyleLean;
}

export interface LineupPlayer {
  player_id: number | null;
  player_key?: string | null;
  name?: string | null;
  shirt_number?: number | null;
  href?: string | null;
  slot?: string | null;
  grid?: string | null;
  role_code?: string | null;
  role_label?: string | null;
  role_family?: string | null;
  role_fit?: number | null;
  score?: number | null;
  confidence: string;
  starts?: number | null;
  minutes?: number | null;
  recency_start?: number | null;
  form?: number | null;
  recent_rating?: number | null;
  recent_rating_score?: number | null;
  rating_count?: number | null;
  rating_coverage?: string | null;
  last_seen?: string | null;
  reason?: string | null;
  position_group?: string | null;
  available?: boolean | null;
  unavailable_reason?: string | null;
  status?: string | null;
  availability_status?: string | null;
  availability_confidence?: string | null;
  availability_source?: string | null;
  availability_source_url?: string | null;
  availability_verified_at?: string | null;
  availability_note?: string | null;
  availability_conflict?: boolean | null;
  availability_downgrade?: number | null;
}

export interface LineupBlock {
  status: string;
  reason?: string | null;
  basis?: string | null;
  team_id?: number | string | null;
  formation?: string | null;
  formation_confidence?: string | null;
  team_confidence?: string | null;
  filled: number;
  coverage: {
    fixtures_with_lineups?: number;
    fixtures_total?: number | null;
    lineup_coverage?: number | null;
    window?: number;
  };
  selection?: {
    weights?: Record<string, number>;
    rating_coverage?: Record<string, number>;
    note?: string;
  };
  disclaimer: string;
  unavailable: Array<{ player_id: number; name: string; reason: string }>;
  unknowns: string[];
  availability?: {
    state?: string;
    applicable?: boolean;
    known?: number | null;
    unknown?: number | null;
    out?: number | null;
    suspended?: number | null;
    doubtful?: number | null;
    returned?: number | null;
    conflicts?: number | null;
    as_of?: string | null;
    source_ids?: string[];
    note?: string;
  };
  selection_risks?: Array<{
    player_id?: number | null;
    name?: string | null;
    status?: string;
    note?: string | null;
  }>;
  players: LineupPlayer[];
  contenders: LineupPlayer[];
  note?: string | null;
  assignment_note?: string | null;
}

export interface MatchdayReadBullet {
  text: string;
  basis: "measured" | "inferred" | "unknown" | string;
}

export interface MatchdayReadKey {
  label: string;
  text: string;
  basis: "measured" | "inferred" | "unknown" | string;
}

export interface MatchdayRead {
  headline: string;
  bullets: MatchdayReadBullet[];
  keys: MatchdayReadKey[];
  basis: string;
  note: string;
}

export interface MatchdayHeadToHead {
  date: string;
  competition_name?: string | null;
  home_team_name: string;
  away_team_name: string;
  home_goals?: number | null;
  away_goals?: number | null;
  venue: "H" | "A" | string;
  result?: string | null;
}

export interface MatchdayDocument {
  schema_version: string;
  generated_at: string;
  season: string;
  state: "fresh" | "stale" | "no_fixture" | "unavailable" | string;
  stale_reason?: string | null;
  served_generated_at?: string | null;
  fixture: MatchdayFixture | null;
  next_fixtures: MatchdayFixture[];
  teams: Record<string, MatchdayTeam>;
  form_guide: Record<string, FormBlock>;
  head_to_head: MatchdayHeadToHead[];
  strength: Record<string, MatchdayStrength>;
  strength_comparison: {
    status?: string;
    position_gap?: number;
    ppg_gap?: number | null;
    descriptor?: string;
    edge?: string;
    confidence?: string;
    cross_tier?: boolean;
    tier_gap?: number | null;
    note?: string;
    reason?: string;
  };
  styles: Record<string, StylePair>;
  predicted_lineups: Record<string, LineupBlock | null>;
  matchup_read: MatchdayRead | null;
  coverage: {
    state?: string;
    snapshot?: Record<string, unknown>;
    lineups?: Record<string, string>;
    form?: string;
    style?: string;
    possession?: string;
    note?: string;
  };
  sources: MatchdaySource[];
  notes: string;
}

export interface ProvenanceSourceRef {
  id: string;
  name: string;
  url?: string | null;
  verified_at?: string | null;
  lane?: string | null;
  attribution?: string | null;
}

export interface ProvenanceLayerSource {
  source_id: string;
  role: "primary" | "fallback" | "corroboration" | "optional" | string;
  name: string;
  url?: string | null;
  verified_at?: string | null;
  rows?: number | null;
}

export interface ProvenanceLayer {
  id: string;
  label: string;
  kind: string;
  status: string;
  scope: string;
  fields: string[];
  primary: string;
  primary_source?: ProvenanceSourceRef | null;
  fallback: string[];
  sources: ProvenanceLayerSource[];
  gate?: {
    id?: string | null;
    status: string;
    report?: string | null;
    reason?: string | null;
  } | null;
  surfaces: string[];
  note?: string | null;
}

export interface ProvenanceSourceSummary {
  id: string;
  name: string;
  url?: string | null;
  lane?: string | null;
  attribution?: string | null;
  last_verified?: string | null;
  primary_layers: string[];
  rows: number;
  rows_basis: string;
}

export interface ProvenanceDocument {
  schema_version: string;
  generated_at: string;
  season: string;
  layers: ProvenanceLayer[];
  sources: ProvenanceSourceSummary[];
  excluded: Array<{ id: string; reason: string }>;
  migration: {
    season: string;
    enabled: boolean;
    gate_status: string;
    active_source: string;
    report?: string | null;
    reason?: string | null;
  };
  availability: {
    status: string;
    provider_snapshot: string;
    reason?: string | null;
  };
  notes: string;
}

export interface AvailabilityEntry {
  player_id?: number | null;
  player_key?: string | null;
  player_name?: string | null;
  status: "out" | "doubtful" | "suspended" | "returned" | "available" | "unknown" | string;
  reason_category?: string;
  reason?: string | null;
  expected_return?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  source_id?: string;
  source_url?: string | null;
  source_title?: string | null;
  verified_at?: string | null;
  confidence?: string;
  stale?: boolean;
  provider_signal?: string | null;
  conflict?: boolean;
  in_squad?: boolean;
  note?: string | null;
}

export interface AvailabilityDocument {
  schema_version: string;
  generated_at: string;
  season: string;
  club_id: string;
  state: string;
  as_of?: string | null;
  policy_version: string;
  coverage: {
    status: string;
    entries: number;
    known: number;
    unknown: number;
    out: number;
    suspended: number;
    doubtful: number;
    returned: number;
    stale: number;
    conflicts: number;
    provider_snapshot: Record<string, unknown>;
    note: string;
  };
  entries: AvailabilityEntry[];
  sources: MatchdaySource[];
  notes: string;
}

export interface NeedsPlayer {
  player_id?: number | null;
  name?: string | null;
  role_family?: string | null;
  starts?: number | null;
  minutes?: number | null;
  sub_apps?: number | null;
  category?: string | null;
  availability_status?: string | null;
  availability_note?: string | null;
  availability_conflict?: boolean | null;
  arrival?: string | null;
  arrival_kind?: string | null;
  note?: string | null;
}

export interface NeedsFamily {
  family: string;
  label: string;
  category: "cover" | "replace" | "strengthen" | "monitor" | "none" | "unknown" | string;
  priority?: number | null;
  urgency: string;
  measured_score?: number | null;
  curated_prior?: number | null;
  confidence: string;
  basis: string;
  expected_slots?: number | null;
  measured: Record<string, unknown>;
  evidence: Array<{
    label: string;
    value: string | number | null;
    note?: string | null;
    basis?: string;
  }>;
  drivers: string[];
  availability: Array<Record<string, unknown>>;
  outgoing_risk: Record<string, unknown>;
  replace_status: string;
  scouting_groups: string[];
  role_profile: Record<string, unknown>;
  market_route: {
    primary?: string;
    alternatives?: string[];
    horizon?: string | null;
    fee_expectation?: string;
    budget_status?: string;
    wage_status?: string;
    note?: string;
  };
  roster_space: {
    status?: string;
    max_squad?: number;
    current?: number;
    outgoing_first?: boolean;
    note?: string;
  };
  players: NeedsPlayer[];
  caveats: string[];
  links: Array<{ label: string; href: string }>;
}

export interface NeedsDocument {
  schema_version: string;
  generated_at: string;
  season: string;
  club_id: string;
  state: string;
  summary: {
    families?: number;
    counts?: Record<string, number>;
    top_priority?: string | null;
    availability_known?: number;
    availability_unknown?: number;
    note?: string;
  };
  coverage: Record<string, unknown>;
  roster_space: Record<string, unknown>;
  families: NeedsFamily[];
  sources: MatchdaySource[];
  notes: string;
}

export interface Manifest {
  schema_version: string;
  dataset_version: string;
  generated_at: string;
  season: string;
  profile: string;
  freshness?: {
    dataset_stale_after_hours: number;
    availability_stale_after_days: number;
  };
  sources: Array<{
    id: string;
    name: string;
    lane: string;
    status: string;
    rows: number;
    last_verified?: string;
    attribution?: string;
    layers?: string[];
    rows_basis?: string;
  }>;
  marts: Array<{ id: string; path: string; rows: number; season: string }>;
  consistency?: {
    path: string;
    checksum: string;
    status: string;
    checks: number;
    passed: number;
    failed: number;
  };
  coverage: {
    season: string;
    competitions: Array<{
      id: string;
      name: string;
      matches: number;
      expected_matches: number;
      coverage: string;
      events: number;
      player_stats: number;
    }>;
    cups?: Array<{
      id: string;
      name: string;
      matches?: number;
      ties?: number;
      official_ties?: number;
      groups?: number;
      coverage: string;
      note?: string;
    }>;
    transfers?: {
      club: string;
      count: number;
      confirmed: number;
      curated: number;
      note: string;
    };
    former_players?: {
      club: string;
      count: number;
      with_api_id: number | null;
      with_post_seasons: number | null;
      sell_on_computed: number | null;
      state: string;
      note: string;
    };
    rumours?: {
      club: string;
      count: number;
      active: number;
      note: string;
    };
    forum?: {
      source: string;
      topics: number;
      posts: number;
      first_page_only: boolean;
      raw_posts_published: boolean;
      note: string;
    };
    history?: {
      club: string;
      seasons: number;
      completed: number;
      staff: number;
      honours: number;
      analytics: Record<string, string>;
      note: string;
    };
    provenance?: Record<string, unknown>;
    availability?: Record<string, unknown>;
    needs?: Record<string, unknown>;
    case?: {
      club: string;
      season: string;
      state: string;
      count: number;
      domains: number;
      benchmark_rows: number;
      note?: string | null;
    };
  };
  provenance?: {
    path: string;
    checksum: string;
    layers: number;
    migration?: Record<string, unknown>;
    availability?: Record<string, unknown>;
  };
  files: Array<{ path: string; bytes: number; checksum: string }>;
  validation?: {
    status: string;
    report: string;
    checksum: string;
    generated_at: string;
    season: string;
    strict: boolean;
    errors: number;
    warnings: number;
    checks: number;
  };
  metrics?: {
    registry_path: string;
    registry_checksum: string;
    registry_version: string;
    registry_reviewed: string;
    audit_path: string;
    audit_checksum: string;
    status: string;
    metrics_total: number;
    metrics_passed: number;
    metrics_failed: number;
    parameters_total: number;
    parameters_passed: number;
    parameters_failed: number;
    verification_modes: Record<string, number>;
    provenance_only: number;
    audited_at: string;
    allowlist: {
      status: string;
      entries: Array<Record<string, unknown>>;
      expires: string | null;
    };
  };
}

export interface MetricDefinition {
  id: string;
  label: string;
  description: string;
  value_type: string;
  fields: string[];
  formula: string | Record<string, string>;
  inputs: string[];
  unit: string;
  aggregation: string;
  denominator: string | Record<string, string> | null;
  rounding: Record<string, unknown> | Record<string, Record<string, unknown>>;
  basis: string;
  source_layer: string;
  coverage_tier: string;
  confidence_rule: string;
  home_payload: string;
  payload_paths: string[];
  home_surface: string;
  displayed_surfaces: string[];
  verification: string;
  verification_checks: Array<Record<string, string>>;
  implementation: string | null;
  source_paths: string[];
  limitations: string[];
  owner: string;
  reviewed: string;
  version: number;
  status: string;
}

export interface ParameterDefinition {
  id: string;
  label: string;
  kind: string;
  value: unknown;
  unit: string;
  used_by: string[];
  config_path: string;
  config_keys?: string[];
  verification: string;
  owner: string;
  reviewed: string;
  version: number;
}

export interface MetricsRegistry {
  schema_version: number;
  registry_version: string;
  reviewed: string;
  owner: string;
  change_policy: Record<string, string | boolean>;
  structural_number_patterns: string[];
  metrics: MetricDefinition[];
  parameters: ParameterDefinition[];
  checksum: string;
}

export interface MetricAuditEntry {
  id: string;
  label: string;
  description: string;
  value_type: string;
  verification: string;
  provenance_only: boolean;
  status: string;
  home_payload: string;
  home_surface: string;
  displayed_surfaces: string[];
  source_layer: string;
  basis: string;
  coverage_tier: string;
  payloads: number;
  numeric_leaves: number;
  locations: Array<{
    payload: string;
    pointer: string;
    nodes: number;
    numeric_leaves: number;
  }>;
  rows_checked: number;
  fields_checked: number;
  checks: Array<{ name: string; status: string; message: string }>;
  errors: string[];
  limitations: string[];
  version: number;
}

export interface ParameterAuditEntry {
  id: string;
  label: string;
  status: string;
  kind: string;
  config_path: string;
  config_keys: string[];
  unit: string;
  used_by: string[];
  expected_checksum: string;
  actual_checksum: string | null;
  mismatches: string[];
  errors: string[];
  version: number;
}

export interface MetricsAudit {
  schema_version: string;
  registry_version: string;
  registry_checksum: string;
  registry_reviewed: string;
  dataset_version: string;
  generated_at: string;
  audited_at: string;
  season: string;
  status: string;
  summary: {
    metrics_total: number;
    metrics_passed: number;
    metrics_failed: number;
    parameters_total: number;
    parameters_passed: number;
    parameters_failed: number;
    verification_modes: Record<string, number>;
    provenance_only: number;
    rows_checked: number;
    fields_checked: number;
  };
  metrics: MetricAuditEntry[];
  parameters: ParameterAuditEntry[];
  allowlist: {
    status: string;
    entries: Array<Record<string, unknown>>;
    expires: string | null;
  };
  errors: string[];
}

export interface ConsistencyReport {
  schema_version: string;
  generated_at: string;
  status: string;
  checks: number;
  passed: number;
  failed: number;
  results: Array<{
    id: string;
    description: string;
    status: string;
    rows_checked: number;
    fields_checked: number;
    errors: string[];
    payloads: string[];
  }>;
}

export interface ValidationReport {
  schema_version: string;
  season: string;
  generated_at: string;
  strict: boolean;
  status: string;
  errors: number;
  warnings: number;
  checks: Array<{ name: string; level: string; message: string; value?: unknown }>;
}

export interface CaseSource {
  id: string;
  name: string;
  url?: string | null;
  verified_at?: string | null;
}

export interface CaseOwnerView {
  label: string;
  text: string;
  attribution: string;
}

export interface CaseChairmanFrame {
  label: string;
  text: string;
  source: string;
  note: string;
}

export interface CaseEvidence {
  metric: string;
  count: string;
  sample: string;
  period: string;
  status: "supported" | "mixed" | "not_supported" | "cant_test" | string;
  source: string;
  note?: string | null;
}

export interface CaseLink {
  label: string;
  href: string;
}

export interface CaseClaim {
  id: string;
  domain: "matchday" | "off_pitch" | "chairman" | string;
  order: number;
  title: string;
  claim: string;
  count: string;
  status: "supported" | "mixed" | "not_supported" | "cant_test" | string;
  status_reason: string;
  evidence: CaseEvidence[];
  better_data: string;
  change_mind: string;
  links: CaseLink[];
}

export interface CaseBenchmark {
  title: string;
  note: string;
  columns: string[];
  rows: Array<Record<string, unknown>>;
}

export interface CaseCoverage {
  status: string;
  season: string;
  availability_feed: string;
  historical_appearances: string;
  missing: string[];
  note: string;
}

export interface CaseDocument {
  schema_version: string;
  generated_at: string;
  season: string;
  club_id: string;
  state: string;
  stale_reason?: string | null;
  served_generated_at?: string | null;
  title: string;
  owner_view: CaseOwnerView;
  chairman_frame: CaseChairmanFrame;
  thesis: string;
  claims: CaseClaim[];
  benchmark: CaseBenchmark;
  coverage: CaseCoverage;
  sources: CaseSource[];
  notes: string;
}

export interface SearchEntry {
  type: string;
  id: string;
  name: string;
  slug: string;
  href?: string;
}

function readJson<T>(...segments: string[]): T | null {
  const file = path.join(DATA_DIR, ...segments);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

export function getManifest(): Manifest | null {
  return readJson<Manifest>("manifest.json");
}

export function getTableFiles(): TableFile[] {
  const dir = path.join(DATA_DIR, "tables");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => name.endsWith(".json"))
    .map((name) => readJson<TableFile>("tables", name))
    .filter((table): table is TableFile => table !== null)
    .sort((a, b) => a.tier - b.tier);
}

export function getTable(tier: string): TableFile | null {
  return (
    getTableFiles().find(
      (table) => table.competition_id.split(":")[1] === tier,
    ) ?? null
  );
}

export function getAberdeen(): ClubFile | null {
  return readJson<ClubFile>("clubs", "aberdeen.json");
}

export function getHistory(): HistoryIndex | null {
  return readJson<HistoryIndex>("history", "aberdeen.json");
}

export function getHistorySeason(season: string): HistorySeasonDocument | null {
  return readJson<HistorySeasonDocument>("history", "seasons", `${season}.json`);
}

export function getMatchday(): MatchdayDocument | null {
  return readJson<MatchdayDocument>("matchday", "upcoming.json");
}

export function getProvenance(): ProvenanceDocument | null {
  return readJson<ProvenanceDocument>("provenance.json");
}

export function getAvailability(): AvailabilityDocument | null {
  return readJson<AvailabilityDocument>("availability", "aberdeen.json");
}

export function getNeeds(): NeedsDocument | null {
  return readJson<NeedsDocument>("needs", "aberdeen.json");
}

export function getCompetitionIndex(): CompetitionIndex | null {
  return readJson<CompetitionIndex>("competitions", "index.json");
}

export function getLeagueCup(): LeagueCupFile | null {
  return readJson<LeagueCupFile>("competitions", "league-cup.json");
}

export function getScottishCup(): ScottishCupFile | null {
  return readJson<ScottishCupFile>("competitions", "scottish-cup.json");
}

export function getTransfers(): TransfersFile | null {
  return readJson<TransfersFile>("transfers", "aberdeen.json");
}

export function getFormerPlayers(): FormerPlayersFile | null {
  return readJson<FormerPlayersFile>("former-players", "aberdeen.json");
}

export function getFormerSeasons(): FormerSeasonsFile | null {
  return readJson<FormerSeasonsFile>("former-players", "seasons.json");
}

export function getTransferAudit(): TransferAudit | null {
  return readJson<TransferAudit>("transfers", "aberdeen.audit.json");
}

export function getPlayerPage(playerId: string | number): PlayerPageDocument | null {
  return readJson<PlayerPageDocument>("players", `${playerId}.json`);
}

export function getSquad(): SquadFile | null {
  return readJson<SquadFile>("squad", "aberdeen.json");
}

export function getRumours(): RumoursFile | null {
  return readJson<RumoursFile>("rumours", "aberdeen.json");
}

export function getRumourProfile(): RumourProfile | null {
  return readJson<RumourProfile>("rumours", "profile.json");
}

export function getForumSignal(): ForumSignalFile | null {
  return readJson<ForumSignalFile>("forum", "afc_chat.json");
}

export function getSearchIndex(): SearchEntry[] {
  return readJson<SearchEntry[]>("search-index.json") ?? [];
}

export function getCase(): CaseDocument | null {
  return readJson<CaseDocument>("themes", "aberdeen.json");
}

export interface AnalysisFixture {
  fixture_id: number | string | null;
  match_id?: string | null;
  date: string;
  kickoff: string | null;
  kickoff_tz?: string;
  kickoff_status?: string | null;
  competition_id: string;
  competition_name: string;
  stage?: string | null;
  opponent_name: string;
  venue: "H" | "A" | "N";
  neutral: boolean;
  status: string;
  conflict_review: boolean;
  source_id: string;
}

export interface AnalysisOfficial {
  player_id: number;
  player_name: string | null;
  status: string;
  reason: string | null;
  reason_category: string | null;
  expected_return: string | null;
  confidence: string | null;
  source_id: string | null;
  source_url: string | null;
  verified_at: string | null;
  note: string | null;
}

export interface AnalysisSuspension {
  player_id: number;
  player_name: string | null;
  competition_id: string;
  competition_name: string;
  cautions: number;
  threshold: number | null;
  reds: number;
  red_type: string | null;
  reason: string | null;
  status: string;
  rule_verified: boolean;
  rule_source: string | null;
  last_card_date: string | null;
  next_fixture: {
    fixture_id: number | string | null;
    date: string;
    competition_id: string;
    opponent_name: string;
  } | null;
}

export interface AnalysisInference {
  player_id: number;
  player_name: string | null;
  role_label: string | null;
  fixtures: Array<{ fixture_id: number; date: string; competition: string }>;
  in_squad_of_six: number;
  starts_of_six: number;
  bench_of_six: number;
  confidence: string;
  basis: string;
  note: string;
}

export interface AnalysisSelection {
  player_id: number | null;
  player_name: string | null;
  role_label: string | null;
  confidence: string;
  score: number | null;
  basis: string;
  note: string;
}

export interface AnalysisAim {
  id: string;
  label: string;
  target: string;
  current: string;
  status: string;
  gap: number | null;
  basis: string;
  note: string;
}

export interface AnalysisLensRow {
  player_id: number;
  player_name: string | null;
  age: number | null;
  role_label: string | null;
  role_family: string | null;
  minutes: number;
  minutes_share: number | null;
  rating_percentile: number | null;
  cohort_n: number | null;
  role_depth: number;
  needs_priority: number | null;
}

export interface AnalysisLens {
  label: string;
  definition: string;
  count: number;
  rows: AnalysisLensRow[];
}

export interface AnalysisSummary {
  schema_version: string;
  season: string;
  generated_at: string;
  state: string;
  stale_reason?: string;
  hero: {
    position?: number | null;
    played?: number | null;
    points?: number | null;
    goal_difference?: number | null;
    form?: string | null;
    league_name?: string | null;
  };
  next_up: AnalysisFixture[];
  availability: {
    counts: Record<string, number>;
    official: AnalysisOfficial[];
    suspensions: AnalysisSuspension[];
    inferred: AnalysisInference[];
    selection: AnalysisSelection[];
    coverage: Record<string, unknown>;
    note: string;
  };
  aims: AnalysisAim[];
  squad_decisions: {
    denominator: Record<string, unknown>;
    rows: AnalysisLensRow[];
    lenses: Record<string, AnalysisLens>;
    loans: Array<{
      player_id: number;
      player_name: string | null;
      club: string | null;
      end_date: string | null;
      status: string;
      note: string;
    }>;
    contract: { status: string; note: string };
    coverage: Record<string, number>;
  };
  bridges: Array<{ label: string; href: string; summary: string }>;
  coverage: {
    availability: { known: number; unknown: number; active: number };
    cards?: Record<string, { played: number; covered: number; complete: boolean }>;
    bench?: { fixtures: number; named_bench_complete: number };
    schedule?: { rows: number; scheduled: number; conflicts: number; overdue: number };
    qualification?: string;
    limitations?: string[];
  };
  sources: string[];
  notes: string;
}

export function getAnalysisSummary(): AnalysisSummary | null {
  return readJson<AnalysisSummary>("analysis", "summary.json");
}

export interface FixtureIndexRow {
  fixture_id: number;
  season: string;
  date: string;
  competition_id: string;
  competition_name: string;
  home_team_name: string;
  away_team_name: string;
  aberdeen_is_home?: boolean;
  home_goals: number | null;
  away_goals: number | null;
  home_penalties?: number | null;
  away_penalties?: number | null;
  result: "W" | "D" | "L";
  aberdeen_result: "W" | "D" | "L";
  result_label?: string;
  aberdeen_result_label?: string;
  shootout_result?: string | null;
  decided_by?: string;
  outcome?: "W" | "D" | "L";
  aberdeen_outcome?: "W" | "D" | "L";
  depth: "full" | "result" | "partial" | "score";
  href: string;
}

export interface FixtureIndexAlias {
  fixture_id: number;
  canonical_fixture_id: number;
  canonical_href: string;
  href: string;
}

export interface ScheduledFixtureRow {
  fixture_id: number | string;
  season: string;
  date: string;
  kickoff: string | null;
  kickoff_status: string | null;
  competition_id: string;
  competition_name: string;
  stage: string | null;
  home_team_name: string;
  away_team_name: string;
  aberdeen_is_home: boolean;
  opponent_name: string;
  venue: string | null;
  neutral: boolean;
  status: "scheduled" | "conflict_review" | "postponed" | "cancelled" | "abandoned" | "unknown" | string;
  conflict_review: boolean;
  source_id: string;
}

export interface FixtureIndex {
  schema_version: string;
  generated_at: string;
  count: number;
  fixtures: FixtureIndexRow[];
  scheduled?: ScheduledFixtureRow[];
  scheduled_count?: number;
  schedule_coverage?: {
    schedule_rows?: number;
    scheduled?: number;
    conflicts?: number;
    overdue?: number;
    remaining_is_minimum?: boolean;
    remaining_note?: string;
    source?: string;
  };
  aliases?: FixtureIndexAlias[];
  state?: string;
  stale_reason?: string;
}

export interface FixtureStatsRow {
  key: string;
  label: string;
  home: number | string | null;
  away: number | string | null;
  source: string;
  basis: string;
}

export type MatchSide = "home" | "away";

export interface FixtureScoreboardGoal {
  minute: number | null;
  extra_minute: number | null;
  side: MatchSide;
  team_name: string;
  player_name: string | null;
  assist_name: string | null;
  is_penalty: boolean;
  is_own_goal: boolean;
  score_after: { home: number; away: number };
}

export interface FixtureScoreboardRedCard {
  minute: number | null;
  extra_minute: number | null;
  side: MatchSide;
  team_name: string;
  player_name: string | null;
  card_type: "straight_red" | "second_yellow";
  detail: string | null;
}

export interface FixtureScoreboardSide {
  side: MatchSide;
  team_id: string;
  team_name: string;
  is_aberdeen: boolean;
  goals: FixtureScoreboardGoal[];
  red_cards: FixtureScoreboardRedCard[];
}

export interface FixtureScoreboard {
  home: FixtureScoreboardSide;
  away: FixtureScoreboardSide;
  shootout: { home: number; away: number } | null;
  events_available: boolean;
  goals_complete: boolean;
  note: string;
}

export interface FixtureTimelineRow {
  minute: number | null;
  extra_minute: number | null;
  team_name: string | null;
  player_name: string | null;
  assist_name: string | null;
  event_type: string | null;
  detail: string | null;
  comments: string | null;
  side: MatchSide | null;
  beneficiary_side: MatchSide | null;
  card_type: "straight_red" | "second_yellow" | null;
  is_goal: boolean;
  is_own_goal: boolean;
  is_penalty: boolean;
  is_shootout: boolean;
  is_red_card: boolean;
  is_second_yellow: boolean;
  is_missed_penalty: boolean;
  is_var: boolean;
  score_after: { home: number; away: number };
}

export interface FixtureLineupPlayer {
  player_id: number | null;
  player_name: string | null;
  shirt_number: number | null;
  position: string | null;
  role?: string | null;
  minutes: number | null;
  grid?: string | null;
  on_minute?: number | null;
}

export interface FixtureLineup {
  team_id: string;
  team_name: string;
  formation: string | null;
  coach_name: string | null;
  starters: FixtureLineupPlayer[];
  substitutes: FixtureLineupPlayer[];
}

export interface FixturePlayerStat {
  player_id: number | null;
  player_name: string | null;
  href?: string | null;
  team_id: number | null;
  team_name: string | null;
  is_aberdeen: boolean | null;
  rating: number | null;
  minutes: number | null;
  goals: number | null;
  assists: number | null;
  shots_total: number | null;
  shots_on: number | null;
  passes_total: number | null;
  pass_accuracy: number | null;
  tackles: number | null;
  duels_won: number | null;
  yellow_cards: number | null;
  red_cards: number | null;
}

export interface FixturePerformancePlayer {
  player_id: number | null;
  player_name: string | null;
  href?: string | null;
  team_name: string | null;
  is_aberdeen: boolean | null;
  rating: number | null;
  minutes: number | null;
  goals: number | null;
  assists: number | null;
  shots_total: number | null;
  shots_on: number | null;
  passes_total: number | null;
  pass_accuracy: number | null;
  tackles: number | null;
  duels_won: number | null;
}

export interface FixtureXgShotProfile {
  shots: number | null;
  shots_on_target: number | null;
  shots_off: number | null;
  shots_blocked: number | null;
  shots_insidebox: number | null;
  shots_outsidebox: number | null;
  penalties: number | null;
  penalty_goals: number | null;
}

export interface FixtureXgSide {
  value: number | null;
  low: number | null;
  high: number | null;
  goals_low: number | null;
  goals_high: number | null;
  goals: number | null;
  goals_minus: number | null;
  goals_position: "below" | "within" | "above" | null;
  provider: number | null;
  provider_source: string | null;
  xg_per_shot: number | null;
  penalty_xg: number | null;
  penalties: number | null;
  penalties_known: boolean | null;
  basis: string | null;
  shot_profile: FixtureXgShotProfile | null;
}

export interface FixtureDocument {
  schema_version: string;
  generated_at: string;
  fixture: {
    fixture_id: number;
    season: string;
    date: string;
    competition_id: string;
    competition_name: string;
    round: string | null;
    status: string;
    venue: "H" | "A";
    venue_name: string | null;
    referee: string | null;
    home_team_id: string;
    home_team_name: string;
    away_team_id: string;
    away_team_name: string;
    home_goals: number | null;
    away_goals: number | null;
    home_ht_goals: number | null;
    away_ht_goals: number | null;
    home_penalties: number | null;
    away_penalties: number | null;
    extra_time: boolean | null;
    result: "W" | "D" | "L";
    aberdeen_result: "W" | "D" | "L";
    href: string;
    duplicate_of?: string | null;
  };
  depth: "full" | "result" | "partial" | "score";
  scoreboard: FixtureScoreboard;
  summary: {
    headline: string;
    basis: string;
    bullets: Array<{ text: string; basis: string }>;
    events_available: boolean;
    goals_complete: boolean;
    reconciliation?: {
      event_goals: number | null;
      event_score: { home: number; away: number } | null;
      final_score: { home: number; away: number };
      matched: boolean | null;
    };
    note: string;
  };
  stats: {
    home: Record<string, number | string | null>;
    away: Record<string, number | string | null>;
    rows: FixtureStatsRow[];
    coverage: Record<string, string>;
  };
  xg: {
    available: boolean;
    home?: FixtureXgSide;
    away?: FixtureXgSide;
    model_id?: string;
    note?: string;
    model_range_level?: number | null;
    goals_range_level?: number | null;
    goals_dispersion?: number | null;
    gate_status?: string | null;
    gate_passed?: boolean | null;
    gate_note?: string | null;
    evaluation_href?: string | null;
  };
  timeline: FixtureTimelineRow[];
  lineups: { home: FixtureLineup | null; away: FixtureLineup | null };
  player_stats: FixturePlayerStat[];
  performance?: {
    available: boolean;
    aberdeen: { basis: string; players: FixturePerformancePlayer[] };
    opponent: { basis: string; players: FixturePerformancePlayer[] };
    strengths: Array<{
      key: string;
      label: string;
      aberdeen: number;
      opponent: number;
      unit: string;
      source: string | null;
    }>;
    note: string;
  };
  form: {
    before: Array<{
      fixture_id: number;
      date: string;
      opponent_name: string;
      venue: "H" | "A";
      goals_for: number | null;
      goals_against: number | null;
      href: string;
    }>;
    after: Array<{
      fixture_id: number;
      date: string;
      opponent_name: string;
      venue: "H" | "A";
      goals_for: number | null;
      goals_against: number | null;
      href: string;
    }>;
  };
  coverage: Record<string, boolean | string>;
  sources: Array<{ id: string; name: string; layer: string; note: string }>;
  links: Record<string, string | null>;
}

export interface XgAggregate {
  scope: "season" | "era" | "last10";
  season: string;
  competition_id: string;
  matches: number;
  fxg: number | null;
  low: number | null;
  high: number | null;
  goals: number;
  goals_low: number | null;
  goals_high: number | null;
  goals_minus_fxg: number | null;
  goals_minus_low: number | null;
  goals_minus_high: number | null;
  goals_position: "below" | "within" | "above" | null;
  shots: number;
  shots_on_target: number;
  penalties: number;
  xg_per_shot: number | null;
  model_range_width: number | null;
  goals_range_width: number | null;
  interval_method: string | null;
  goals_range_method: string | null;
  goals_dispersion: number | null;
}

export interface XgMatch {
  fixture_id: number;
  season: string;
  date: string;
  competition_id: string;
  opponent_id: string;
  opponent_name: string;
  venue: "H" | "A";
  goals_for: number | null;
  goals_against: number | null;
  fxg_for: number | null;
  fxg_for_low: number | null;
  fxg_for_high: number | null;
  fxg_against: number | null;
  fxg_against_low: number | null;
  fxg_against_high: number | null;
  goals_for_low: number | null;
  goals_for_high: number | null;
  goals_against_low: number | null;
  goals_against_high: number | null;
  goals_minus_fxg_for: number | null;
  goals_minus_fxg_for_low: number | null;
  goals_minus_fxg_for_high: number | null;
  goals_minus_fxg_against: number | null;
  goals_minus_fxg_against_low: number | null;
  goals_minus_fxg_against_high: number | null;
  goals_position_for: "below" | "within" | "above" | null;
  goals_position_against: "below" | "within" | "above" | null;
  fxg_per_shot_for: number | null;
  fxg_per_shot_against: number | null;
  shots_for: number | null;
  shots_on_target_for: number | null;
  shots_off_for: number | null;
  shots_blocked_for: number | null;
  shots_insidebox_for: number | null;
  shots_outsidebox_for: number | null;
  penalties_for: number | null;
  penalty_goals_for: number | null;
  shots_against: number | null;
  shots_on_target_against: number | null;
  shots_off_against: number | null;
  shots_blocked_against: number | null;
  shots_insidebox_against: number | null;
  shots_outsidebox_against: number | null;
  penalties_against: number | null;
  penalty_goals_against: number | null;
  basis_for: string | null;
  basis_against: string | null;
  interval_basis: string | null;
  goals_range_basis: string | null;
  fxg_diff: number | null;
  provider_xg_for: number | null;
  provider_xg_against: number | null;
  provider_xg_source: string | null;
  source: string | null;
}

export interface XgProviderEstimate {
  status: "available" | "unavailable" | string;
  label: string;
  basis: "estimate" | string;
  method: string;
  formula?: string;
  coefficients?: { intercept: number; slope: number };
  clamp_min?: number;
  sample: {
    season: string;
    competition_id: string;
    matches: number;
    team_rows: number;
    source: string;
  };
  in_sample_mae?: number;
  loocv_mae?: number | null;
  max_loocv_error?: number | null;
  r2?: number | null;
  loocv_basis?: string;
  reason?: string;
  source: string;
  limitations: string[];
}

export interface XgManagerPerMatch {
  fxg_for: number | null;
  fxg_against: number | null;
  goals_for: number | null;
  goals_against: number | null;
  goals_minus_fxg_for: number | null;
  goals_minus_fxg_against: number | null;
  provider_actual_for: number | null;
  provider_actual_against: number | null;
  provider_estimate_for: number | null;
  provider_estimate_against: number | null;
}

export interface XgManagerSplit {
  season: string;
  competition_id: string;
  scope: "manager_stint" | "season_context" | string;
  stint_id: string | null;
  person_id: string | null;
  manager: string;
  interim: boolean;
  stint_start: string | null;
  stint_end: string | null;
  first_match: string | null;
  last_match: string | null;
  matches: number;
  fxg_for: number | null;
  fxg_against: number | null;
  goals_for: number;
  goals_against: number;
  goals_minus_fxg_for: number | null;
  goals_minus_fxg_against: number | null;
  provider_actual_for: number | null;
  provider_actual_against: number | null;
  provider_actual_matches: number;
  provider_estimate_for: number | null;
  provider_estimate_against: number | null;
  provider_estimate_matches: number;
  provider_basis: "actual" | "estimate" | "actual_partial" | "unavailable" | string;
  comparison_role: "current" | "previous" | "context" | string;
  per_match: XgManagerPerMatch;
  coverage: {
    matches: number;
    with_fxg: number;
    with_provider_actual: number;
    with_provider_estimate: number;
    note: string;
  };
}

export interface XgDocument {
  schema_version: string;
  generated_at: string;
  season: string;
  state?: string;
  stale_reason?: string;
  model: {
    model_id: string;
    label: string;
    status: string;
    method?: string;
    specification?: string | null;
    features?: string[];
    coefficients?: Record<string, number> | null;
    fallback_coefficients?: Record<string, number> | null;
    penalty_xg?: number;
    penalty_source?: string;
    interval_level?: number;
    interval_method?: string;
    interval_basis?: string;
    interval_low_offset?: number;
    interval_high_offset?: number;
    bootstrap?: {
      draws: number;
      seed: number;
      valid_draws: number;
      cluster: string;
    } | null;
    goals_range_method?: string;
    goals_dispersion?: number;
    model_interval_coverage?: number | null;
    goals_range_coverage?: number | null;
    fit_team_rows?: number;
    fit_season?: string | null;
    fit_competition?: string | null;
    calibration?: Record<string, unknown> | null;
    selection?: Record<string, unknown> | null;
    transfer_check?: Record<string, unknown> | null;
    overdispersion?: number;
    fit_matches: number;
    fit_seasons: string[];
    global_rate?: { rate: number; low: number; high: number };
    rates?: Array<Record<string, unknown>>;
    competition_rates?: Array<Record<string, unknown>>;
    evaluation: Record<string, unknown> | null;
  } | null;
  evaluation: {
    status: string;
    method?: string;
    validation_season: string;
    matches: number;
    team_rows?: number;
    bias: number | null;
    mae: number | null;
    calibration_slope: number | null;
    r2?: number | null;
    model_interval_coverage?: number | null;
    goals_range_coverage?: number | null;
    goals_dispersion?: number | null;
    thresholds: Record<string, number>;
    passed: boolean;
    note: string;
  } | null;
  matches: XgMatch[];
  aggregates: XgAggregate[];
  transfer_evaluation?: Record<string, unknown> | null;
  provider_estimate?: XgProviderEstimate | null;
  manager_splits?: XgManagerSplit[];
  coverage: {
    matches: number;
    with_fxg: number;
    with_provider_xg: number;
    missing_team_stats: number;
    with_zones?: number;
    with_penalties?: number;
    enrichment?: {
      status: string;
      season: string;
      league_fixtures: number;
      api_fixtures_matched: number;
      stats_available: number;
      events_available: number;
      zones_available: number;
      penalties_available: number;
      provider_xg_fdco: number;
      missing_feature_matches: number[];
    } | null;
    provider_actual?: {
      total_matches: number;
      league_2026_27: number;
      league_2025_26: number;
      conference_2025_26: number;
      conference_2023_24: number;
      note: string;
    };
    manager_splits?: {
      seasons: string[];
      competition_id: string;
      rows: number;
      unattributed_matches: number;
      note: string;
    };
    note: string;
  };
  sources: Array<{ id: string; name: string; layer: string; note: string }>;
}

export interface ScoutingArchetypeScore {
  score: number | null;
  adjusted_score?: number | null;
  coverage: number | null;
}

export interface ScoutingProfile {
  id: string;
  label: string;
  score: number;
  raw_score?: number | null;
  adjusted_score?: number | null;
}

export interface ScoutingRates {
  goals_p90: number | null;
  assists_p90: number | null;
  goals_assists_p90: number | null;
  shots_p90: number | null;
  dribbles_success_p90: number | null;
  passes_completed_p90: number | null;
  key_passes_p90: number | null;
  tackles_p90: number | null;
  interceptions_p90: number | null;
  pass_completion_pct: number | null;
  duel_win_pct: number | null;
  dribble_success_pct: number | null;
  conversion_pct: number | null;
  save_pct: number | null;
  conceded_p90: number | null;
  saves_p90: number | null;
}

export interface FormerAberdeenProfile {
  player_key: string;
  name: string;
  href: string;
  transfer_href: string | null;
  departure: {
    transfer_id: string | null;
    date: string | null;
    season: string | null;
    window: string | null;
    kind: string | null;
    fee_status: string | null;
    fee_display: string | null;
    to_club_name: string | null;
    to_market: string | null;
    to_country: string | null;
    is_rival: boolean;
    rival_name: string | null;
    source_urls: string[];
  };
  aberdeen: {
    first_season: string | null;
    last_season: string | null;
    appearances: number | null;
    starts: number | null;
    sub_apps: number | null;
    minutes: number | null;
    goals: number | null;
    assists: number | null;
    rating: number | null;
    tenure_coverage: string | null;
    developed_here: string | null;
    developed_basis: string | null;
    final_season: Record<string, unknown> | null;
  };
  post_career: {
    status: string;
    totals: Record<string, number | null>;
    current: FormerCurrent;
    at_rival: boolean;
    rival_current: boolean;
    rival_spells: {
      club: string;
      from_season: string;
      to_season: string;
      current: boolean;
    }[];
    top_flight_abroad: boolean | null;
  };
  sell_on: FormerSellOnClause | null;
  stats_basis: string | null;
}

export interface ScoutingPlayer extends ScoutingRates {
  player_id: number;
  name: string;
  full_name?: string | null;
  club: string;
  stats_club: string;
  current_club_status: string;
  current_club_source: string;
  transferred_at: string | null;
  current_league_name: string | null;
  age: number | null;
  nationality: string | null;
  position_group: string;
  role_family: string | null;
  role_label: string;
  role_status: string;
  role_family_share: number | null;
  minutes: number;
  appearances: number | null;
  rating: number | null;
  rating_percentile: number | null;
  adjusted_percentile: number | null;
  adjustment_basis: string;
  value_index: number | null;
  value_index_coverage: number | null;
  value_index_drivers: string[];
  value_index_basis: string | null;
  scouting_priority: number | null;
  age_multiplier: number | null;
  europe_multiplier: number | null;
  european_league_phase_minutes: number | null;
  european_league_phase_appearances: number | null;
  european_league_phase_competitions: string[];
  european_status: string;
  value_low_gbp: number | null;
  value_high_gbp: number | null;
  value_confidence: string;
  value_method: string;
  cohort_basis: string;
  cohort_n: number;
  team_context_status: string;
  team_rank: number | null;
  team_points: number | null;
  team_played: number | null;
  team_ppg: number | null;
  team_count: number | null;
  team_points_percentile: number | null;
  team_underperforming: boolean | null;
  team_lift: number | null;
  flags: string[];
  archetypes: Record<string, ScoutingArchetypeScore>;
  profile: ScoutingProfile | null;
  rose?: RoseBlock | null;
  former_aberdeen?: FormerAberdeenProfile | null;
}

export interface ScoutingSearchRow {
  i: number;
  n: string;
  c: string;
  sc: string | null;
  l: string;
  na: string | null;
  rf: string | null;
  a: number | null;
  m: number;
  rt: number | null;
  p: number | null;
  ap: number | null;
  vi: number | null;
  vc: number | null;
  cs: string | null;
  gl: number | null;
  ast: number | null;
  g90: number | null;
  sh90: number | null;
  cv: number | null;
  em: number | null;
  es: string | null;
  eu: string[];
  ga: number | null;
  dr: number | null;
  ps: number | null;
  pa: number | null;
  kp: number | null;
  tk: number | null;
  it: number | null;
  dw: number | null;
  tr: number | null;
  tpts: number | null;
  tpc: number | null;
  tl: number | null;
  tc: number | null;
  tu: boolean | null;
  pr: string | null;
  psc: number | null;
  arp: Array<[number, number | null, number | null, number | null]>;
  f: string[];
}

export interface ScoutingSearchDocument {
  schema_version: string;
  season: string;
  generated_at: string;
  state: string;
  min_minutes: number;
  count: number;
  leagues: Array<{
    id: string;
    slug: string;
    name: string;
    country: string;
    players: number;
    searchable: boolean;
    href: string;
  }>;
  role_labels: Record<string, string>;
  profile_labels: Record<string, string>;
  profile_order: string[];
  priority: ScoutingPriorityConfig;
  archetype_min_coverage: number;
  value_model: {
    weights: Record<string, number>;
    min_weight_coverage: number;
    minutes_full: number;
    age_curve: Array<{ max_age: number; factor: number }>;
  };
  team_context: {
    underperforming_ppg_percentile_max: number;
    min_lift: number;
  };
  europe_coverage: ScoutingEuropeCoverage;
  players: ScoutingSearchRow[];
  limitations: string[];
}

export interface ScoutingPoolCoverage {
  players: number;
  rated: number;
  with_minutes_450: number;
  role_players: number;
  role_coverage: number;
  lineups_fetched: number;
  fixtures_played: number;
  note: string;
}

export interface ScoutingPoolDocument {
  schema_version: string;
  season: string;
  generated_at: string;
  league: {
    id: string;
    slug: string;
    name: string;
    country: string | null;
    tier: number | null;
    provider_league_id: number;
  };
  state: string;
  stale_reason?: string;
  min_minutes: number;
  rose_meta?: {
    catalogue: RoseCatalogue;
    min_petals: number;
    method_note: string;
  };
  players: ScoutingPlayer[];
  coverage: ScoutingPoolCoverage;
  limitations: string[];
  sources: Array<{ id: string; name: string; url: string }>;
}

export interface ScoutingPrior {
  season: string;
  minutes: number;
  starts: number;
  rating: number | null;
  role_family?: string | null;
  role_code?: string | null;
  role_starts?: number;
}

export interface ScoutingAvailability {
  status: string;
  confidence: string;
  source_id: string | null;
  source_url: string | null;
  verified_at: string | null;
  note: string | null;
  stale: boolean;
}

export interface ScoutingBoardPlayer {
  player_id: number;
  name: string;
  role_label: string | null;
  minutes: number;
  rating: number | null;
  availability: ScoutingAvailability;
  prior: ScoutingPrior | null;
  first_choice: boolean;
}

export interface ScoutingFamily {
  family: string;
  label: string;
  players: ScoutingBoardPlayer[];
  player_count: number;
  minutes: number;
  average_rating: number | null;
  rating_percentile: number | null;
  cohort: {
    league_id: string;
    role_family: string;
    n: number;
    median: number | null;
    min_minutes: number;
    basis: string;
  };
  status: string;
  reading: string;
  absent_first_choice: number;
  drivers: string[];
  layer0: ScoutingBoardPlayer[];
}

export interface ScoutingBoard {
  league_id: string;
  families: ScoutingFamily[];
  unassigned_layer0?: ScoutingBoardPlayer[];
  summary: {
    families: number;
    below_cohort: number;
    cover_readings: number;
    structural_readings: number;
    insufficient: number;
    layer0_players: number;
  };
}

export interface ScoutingLayerZero {
  player_id: number;
  name: string;
  family: string | null;
  family_label: string;
  role_label: string | null;
  minutes: number;
  rating: number | null;
  status: string;
  confidence: string;
  source_id: string | null;
  source_url: string | null;
  verified_at: string | null;
  note: string | null;
  prior: ScoutingPrior | null;
  first_choice: boolean;
}

export interface ScoutingSquadRow extends ScoutingRates {
  player_id: number;
  name: string;
  role_family: string | null;
  role_label: string;
  minutes: number;
  minutes_scope?: string;
  league_minutes?: number | null;
  rating: number | null;
  league_rating?: number | null;
  rating_percentile: number | null;
  goals: number | null;
  assists: number | null;
  archetypes: Record<string, ScoutingArchetypeScore>;
  profile: ScoutingProfile | null;
  cohort: { n: number; basis: string };
}

export interface ScoutingLeader {
  player_id: number;
  name: string;
  club: string;
  league_id: string;
  league_slug: string;
  league_name: string;
  stats_club: string;
  current_club_status: string;
  age: number | null;
  minutes: number;
  rating: number | null;
  rating_percentile: number | null;
  adjusted_percentile: number | null;
  raw_score: number | null;
  adjusted_score: number | null;
  coverage: number | null;
  value_index: number | null;
  value_index_coverage: number | null;
  team_context_status?: string;
  team_rank?: number | null;
  team_points?: number | null;
  team_played?: number | null;
  team_ppg?: number | null;
  team_count?: number | null;
  team_points_percentile?: number | null;
  team_underperforming?: boolean | null;
  team_lift?: number | null;
  scouting_priority: number | null;
  bias?: number | null;
  assist_score?: number | null;
  goal_score?: number | null;
  age_multiplier: number | null;
  europe_multiplier: number | null;
  european_league_phase_minutes: number | null;
  european_league_phase_competitions: string[];
  european_status: string;
}

export interface ScoutingGoalScorer {
  player_id: number;
  name: string;
  club: string;
  stats_club: string;
  league_id: string;
  league_slug: string;
  league_name: string;
  age: number | null;
  minutes: number;
  goals: number | null;
  assists: number | null;
  goals_p90: number | null;
  assists_p90: number | null;
  goals_assists_p90: number | null;
  shots_p90: number | null;
  conversion_pct: number | null;
  scouting_priority: number | null;
  value_index: number | null;
  european_status: string;
  european_league_phase_minutes: number | null;
  current_club_status: string;
}

export interface ScoutingAttackerGroup {
  profile_id: string;
  label: string;
  leaders: ScoutingLeader[];
}

export interface ScoutingAttackers {
  assist_bias: ScoutingAttackerGroup;
  goal_bias: ScoutingAttackerGroup;
  goal_scoring: ScoutingGoalScorer[];
  note: string;
}

export interface ScoutingArchetypeDefinition {
  id: string;
  label: string;
  description: string | null;
  families: string[];
  features: Record<string, number>;
  leaders: ScoutingLeader[];
}

export interface ScoutingPivot {
  label: string;
  current: Record<
    string,
    {
      player_id: number;
      name: string;
      role_label: string;
      minutes: number;
      score: number;
      coverage: number | null;
    } | null
  >;
  pool: Record<string, ScoutingLeader[]>;
  archetype_labels: Record<string, string>;
  hypothesis: string;
}

export interface ScoutingLeagueSummary {
  id: string;
  slug: string;
  name: string;
  country: string;
  tier: number | null;
  provider_league_id: number;
  status: string;
  searchable: boolean;
  players: number;
  rated: number;
  with_minutes_450: number;
  role_players: number;
  role_coverage: number;
  lineups_fetched: number;
  fixtures_played: number;
  error: string | null;
  href: string;
}

export interface ScoutingPriorityConfig {
  u23_max_age: number;
  u23_multiplier: number;
  europe_minutes_threshold: number;
  europe_multiplier: number;
}

export interface ScoutingEuropeCompetition {
  competition_id: string;
  competition: string;
  provider_league_id: number;
  fixtures_total: number;
  league_phase: number;
  played: number;
  fetched: number;
  missing: number;
  players: number;
  complete?: boolean;
  error?: string | null;
}

export interface ScoutingEuropeCoverage {
  schema_version?: string;
  season?: string;
  generated_at?: string;
  coverage_complete?: boolean;
  competitions?: ScoutingEuropeCompetition[];
  players?: number;
  requests?: number;
  budget?: number;
  stopped_on_budget?: boolean;
}

export interface ScoutingValueGate {
  min_anchors: number;
  anchor_count: number;
  min_role_anchors: number;
  role_counts: Record<string, number>;
  role_pass: boolean;
  league_tiers: number;
  min_league_tiers: number;
  tier_pass: boolean;
  age_bands: number;
  min_age_bands: number;
  age_pass: boolean;
  top_tier_share: number;
  top_tier_required: number;
  top_tier_pass: boolean;
  passed: boolean;
}

export interface ScoutingValueModel {
  state: string;
  anchor_count: number;
  usable_anchors: number;
  gate: ScoutingValueGate;
  sample: number | null;
  coefficients: Record<string, number | null> | null;
  residual_sd: number | null;
  in_sample_mae: number | null;
  loocv_mae: number | null;
  max_loocv_error: number | null;
  r2: number | null;
  interval: number;
  index: {
    weights?: Record<string, number>;
    minutes_full?: number;
    min_weight_coverage?: number;
    age_curve?: Array<{ max_age: number; factor: number }>;
  };
  limitations: string[];
}

export interface ScoutingDocument {
  schema_version: string;
  season: string;
  generated_at: string;
  state: string;
  stale_reason?: string;
  club_id: string;
  board: ScoutingBoard;
  layer_zero: ScoutingLayerZero[];
  squad: ScoutingSquadRow[];
  archetypes: ScoutingArchetypeDefinition[];
  attackers: ScoutingAttackers;
  team_lens?: {
    label: string;
    definition: string;
    threshold: number | null;
    leaders: ScoutingLeader[];
    coverage: Record<string, number>;
  };
  value_model: ScoutingValueModel;
  priority: ScoutingPriorityConfig;
  europe_coverage: ScoutingEuropeCoverage;
  leagues: ScoutingLeagueSummary[];
  coverage: {
    totals: Record<string, number>;
    known_gaps: string[];
    sources: Array<{ id: string; name: string; url: string; coverage?: string }>;
  };
  limitations: string[];
}

export interface ScoutingCoverageDocument {
  schema_version: string;
  season: string;
  generated_at: string;
  state?: string;
  stale_reason?: string;
  provider: string;
  cohort_minutes: number;
  leagues: ScoutingLeagueSummary[];
  totals: Record<string, number>;
  known_gaps: string[];
  sources: Array<{ id: string; name: string; url: string; coverage?: string }>;
}

export function getFixtureIndex(): FixtureIndex | null {
  return readJson<FixtureIndex>("fixtures", "index.json");
}

export function getFixture(fixtureId: string | number): FixtureDocument | null {
  return readJson<FixtureDocument>("matches", `${fixtureId}.json`);
}

export function getXg(): XgDocument | null {
  return readJson<XgDocument>("xg", "aberdeen.json");
}

export function getScouting(): ScoutingDocument | null {
  return readJson<ScoutingDocument>("scouting", "aberdeen.json");
}

export function getScoutingCoverage(): ScoutingCoverageDocument | null {
  return readJson<ScoutingCoverageDocument>("scouting", "coverage.json");
}

let scoutingSearchCache: ScoutingSearchDocument | null | undefined;

export function getScoutingSearch(): ScoutingSearchDocument | null {
  if (scoutingSearchCache !== undefined) return scoutingSearchCache;
  scoutingSearchCache = readJson<ScoutingSearchDocument>(
    "scouting",
    "search-index.json",
  );
  return scoutingSearchCache;
}

const scoutingPoolCache = new Map<string, ScoutingPoolDocument | null>();

export function getScoutingPool(slug: string): ScoutingPoolDocument | null {
  const cached = scoutingPoolCache.get(slug);
  if (cached !== undefined) return cached;
  const document = readJson<ScoutingPoolDocument>(
    "scouting",
    "pool",
    `${slug}.json`,
  );
  scoutingPoolCache.set(slug, document);
  return document;
}

export interface ScoutingPlayerView {
  primary: ScoutingSearchRow;
  others: ScoutingSearchRow[];
}

export function getScoutingPlayer(
  playerId: string | number,
): ScoutingPlayerView | null {
  const document = getScoutingSearch();
  if (!document) return null;
  const id = Number(playerId);
  const rows = document.players
    .filter((row) => row.i === id)
    .sort((left, right) => right.m - left.m);
  if (!rows.length) return null;
  return { primary: rows[0], others: rows.slice(1) };
}

export function getScoutingPlayerIds(): number[] {
  const document = getScoutingSearch();
  if (!document) return [];
  return Array.from(new Set(document.players.map((row) => row.i))).sort(
    (left, right) => left - right,
  );
}

export function getMetricsRegistry(): MetricsRegistry | null {
  return readJson<MetricsRegistry>("metrics", "registry.json");
}

export function getMetricsAudit(): MetricsAudit | null {
  return readJson<MetricsAudit>("audit", "metrics.json");
}

export function getConsistencyReport(): ConsistencyReport | null {
  return readJson<ConsistencyReport>("audit", "consistency.json");
}

export function getValidationReport(): ValidationReport | null {
  return readJson<ValidationReport>("audit", "validation.json");
}

export function dataAgeHours(manifest: Manifest | null): number | null {
  if (!manifest) return null;
  const generated = Date.parse(manifest.generated_at);
  if (Number.isNaN(generated)) return null;
  return Math.max(0, (Date.now() - generated) / 36e5);
}

export { formatDate } from "@/lib/format";
