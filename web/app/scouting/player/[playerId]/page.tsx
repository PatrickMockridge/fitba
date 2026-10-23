import { notFound } from "next/navigation";
import { ContractPage } from "@/components/ContractPage";
import { ScoutingProfile } from "@/components/ScoutingProfile";
import {
  getScouting,
  getScoutingPlayer,
  getScoutingPlayerIds,
  getScoutingPool,
} from "@/lib/data";

export const dynamicParams = false;

export function generateStaticParams() {
  return getScoutingPlayerIds().map((playerId) => ({ playerId: String(playerId) }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ playerId: string }>;
}) {
  const { playerId } = await params;
  const view = getScoutingPlayer(playerId);
  if (!view) return { title: "Scouting profile · fitba" };
  const pool = getScoutingPool(view.primary.l);
  const player = pool?.players.find((item) => item.player_id === view.primary.i);
  const name = player?.full_name || player?.name || view.primary.n;
  const club = player?.club ?? view.primary.c;
  const league = pool?.league.name ?? view.primary.l;
  const title = `${name} · ${club} · scouting profile · fitba`;
  const description = `${name} at ${club} in ${league}: role, provider percentiles, scouting priority and archetype profile from the licensed feed.`;
  return {
    title,
    description,
    alternates: { canonical: `/scouting/player/${playerId}/` },
    openGraph: { title, description, type: "profile" },
  };
}

export default async function ScoutingPlayerPage({
  params,
}: {
  params: Promise<{ playerId: string }>;
}) {
  const { playerId } = await params;
  const view = getScoutingPlayer(playerId);
  if (!view) notFound();
  const pool = getScoutingPool(view.primary.l);
  const player = pool?.players.find((item) => item.player_id === view.primary.i);
  if (!pool || !player) notFound();
  const hub = getScouting();
  const priority =
    hub?.priority ?? {
      u23_max_age: 23,
      u23_multiplier: 1.3,
      europe_minutes_threshold: 90,
      europe_multiplier: 0.6,
    };
  return (
    <ContractPage surface="scouting-player" state="full">
      <ScoutingProfile
        player={player}
        priority={priority}
        archetypes={hub?.archetypes ?? []}
        others={view.others}
        leagueSlug={pool.league.slug}
        leagueName={pool.league.name}
        roseCatalogue={pool.rose_meta?.catalogue ?? {}}
      />
    </ContractPage>
  );
}
