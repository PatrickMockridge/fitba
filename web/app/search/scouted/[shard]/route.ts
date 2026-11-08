import { getScoutedEntityShard, getScoutedEntityShardCount } from "@/lib/data";

export const dynamic = "force-static";

export function generateStaticParams() {
  return Array.from({ length: getScoutedEntityShardCount() }, (_, shard) => ({
    shard: String(shard),
  }));
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ shard: string }> },
) {
  const { shard } = await params;
  const index = Number(shard);
  if (!Number.isInteger(index) || index < 0 || index >= getScoutedEntityShardCount()) {
    return Response.json({ state: "unknown_shard", entities: [] }, { status: 404 });
  }
  return Response.json({ shard: index, entities: getScoutedEntityShard(index) });
}
