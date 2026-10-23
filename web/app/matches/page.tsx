import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { MatchRecordArchive } from "@/components/MatchRecordArchive";
import { getFixtureIndex } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/matches/" },
  title: "Results and fixtures · fitba",
  description:
    "Every Aberdeen result and known remaining fixture, with the depth the record supports.",
};

export default function MatchesPage() {
  const index = getFixtureIndex();
  if (!index || !index.fixtures.length) {
    return (
      <ContractPage surface="matches" state="empty">
        <section className="page-head" data-contract="matches.hero">
          <p className="eyebrow">Matches</p>
          <h1>Results and fixtures</h1>
          <p className="lede">
            No played fixtures are published in this build. Run{" "}
            <code>uv run fitba publish</code> to generate the record.
          </p>
        </section>
      </ContractPage>
    );
  }
  const scheduledRows = index.scheduled ?? [];
  const upcomingCount = scheduledRows.filter((row) => !row.conflict_review).length;
  const seasons = Array.from(
    new Set([...index.fixtures.map((row) => row.season), ...scheduledRows.map((row) => row.season)]),
  ).sort((a, b) => b.localeCompare(a));
  const currentSeason = seasons[0];
  const seasonGroups = seasons.map((season) => ({
    season,
    rows: index.fixtures.filter((row) => row.season === season),
  }));
  const scheduledGroups = seasons.map((season) => ({
    season,
    rows: scheduledRows.filter((row) => row.season === season),
  }));
  return (
    <ContractPage surface="matches">
      <section className="page-head" data-contract="matches.hero">
        <p className="eyebrow">Cormack era</p>
        <h1>Results and fixtures</h1>
        <p className="lede">
          Every Aberdeen fixture, one season at a time: results with the score,
          events, lineups and measured stats, plus the known remaining fixtures.
          Cup progression and the post-split league games will add to the
          schedule; the count below is therefore a minimum.
        </p>
        <p className="fine-print">
          {index.count} played fixtures · {upcomingCount}+ to play (minimum).{" "}
          <Link className="text-link" href="/analysis/xg/">
            fxG model and aggregates →
          </Link>{" "}
          <Link className="text-link" href="/analysis/">
            Season overview →
          </Link>{" "}
          <Link className="text-link" href="/matchday/">
            Matchday →
          </Link>{" "}
          <Link className="text-link" href="/history/">
            The Cormack era →
          </Link>
        </p>
      </section>

      <MatchRecordArchive
        seasons={seasonGroups}
        scheduled={scheduledGroups}
        current={currentSeason}
        remainingIsMinimum={Boolean(index.schedule_coverage?.remaining_is_minimum)}
      />
    </ContractPage>
  );
}
