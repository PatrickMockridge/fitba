import { getScoutingSearch } from "@/lib/data";

export const dynamic = "force-static";

export function GET() {
  const document = getScoutingSearch();
  if (!document) {
    return Response.json({ state: "empty", players: [] });
  }
  return Response.json(document);
}
