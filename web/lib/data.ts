import fs from "node:fs";
import path from "node:path";

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

export interface TableFile {
  competition_id: string;
  competition_name: string;
  short_name: string;
  tier: number;
  season: string;
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
}

export interface ClubHistory {
  season: string;
  position: number;
  played: number;
  points: number;
  gd: number;
  form: string;
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
  history: ClubHistory[];
  coverage: string;
  notes: string;
}

export interface Manifest {
  schema_version: string;
  dataset_version: string;
  generated_at: string;
  season: string;
  profile: string;
  sources: Array<{
    id: string;
    name: string;
    lane: string;
    status: string;
    rows: number;
    last_verified?: string;
    attribution?: string;
  }>;
  marts: Array<{ id: string; path: string; rows: number; season: string }>;
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
  };
  files: Array<{ path: string; bytes: number; checksum: string }>;
}

export interface SearchEntry {
  type: string;
  id: string;
  name: string;
  slug: string;
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

export function getSearchIndex(): SearchEntry[] {
  return readJson<SearchEntry[]>("search-index.json") ?? [];
}

export function dataAgeHours(manifest: Manifest | null): number | null {
  if (!manifest) return null;
  const generated = Date.parse(manifest.generated_at);
  if (Number.isNaN(generated)) return null;
  return Math.max(0, (Date.now() - generated) / 36e5);
}

export function formatDate(value: string): string {
  const date = new Date(`${value}T12:00:00Z`);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
