import type { MetadataRoute } from "next";
import {
  getFixtureIndex,
  getHistory,
  getScoutingCoverage,
  getSquad,
} from "@/lib/data";

export const dynamic = "force-static";

const SITE_URL = "https://patrickmockridge.github.io/fitba";

const STATIC_ROUTES = [
  "/",
  "/matchday/",
  "/matches/",
  "/analysis/",
  "/analysis/xg/",
  "/squad/",
  "/players/",
  "/scouting/",
  "/scouting/search/",
  "/recruitment/",
  "/transfers/",
  "/loans/",
  "/history/",
  "/competitions/",
  "/competitions/league-cup/",
  "/competitions/scottish-cup/",
  "/fixtures/",
  "/news/",
  "/rumours/",
  "/scotland/",
  "/sources/",
  "/methodology/",
  "/metrics/",
  "/status/",
  "/about/",
  "/corrections/",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const urls = new Set(STATIC_ROUTES.map((path) => `${SITE_URL}${path}`));
  for (const fixture of getFixtureIndex()?.fixtures ?? []) {
    urls.add(`${SITE_URL}/matches/${fixture.fixture_id}/`);
  }
  for (const season of getHistory()?.seasons ?? []) {
    if (season.href) urls.add(`${SITE_URL}${season.href}`);
  }
  for (const player of getSquad()?.players ?? []) {
    if (player.href) urls.add(`${SITE_URL}${player.href}`);
  }
  for (const league of getScoutingCoverage()?.leagues ?? []) {
    urls.add(`${SITE_URL}${league.href}`);
  }
  return [...urls].sort().map((url) => ({ url, lastModified: undefined }));
}
