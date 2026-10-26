import { SCOUTING_SEARCH_SHARDS, getScoutingSearchShard } from "@/lib/data";

export const dynamic = "force-static";

export function generateStaticParams() {
  return Array.from({ length: SCOUTING_SEARCH_SHARDS }, (_, shard) => ({
    shard: String(shard),
  }));
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ shard: string }> },
) {
  const { shard } = await params;
  const index = Number(shard);
  if (!Number.isInteger(index) || index < 0 || index >= SCOUTING_SEARCH_SHARDS) {
    return Response.json({ state: "unknown_shard", players: [] }, { status: 404 });
  }
  return Response.json({ shard: index, players: getScoutingSearchShard(index) });
}
