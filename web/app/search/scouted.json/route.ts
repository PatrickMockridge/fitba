import { getScoutedEntityIndex } from "@/lib/data";

export const dynamic = "force-static";

export function GET() {
  const document = getScoutedEntityIndex();
  if (!document) {
    return Response.json({ state: "empty", entities: [] });
  }
  return Response.json(document);
}
