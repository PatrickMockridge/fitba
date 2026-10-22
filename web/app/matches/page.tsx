import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { MatchRecordArchive } from "@/components/MatchRecordArchive";
import { getFixtureIndex } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/matches/" },
  title: "Match record · fitba",
  description:
    "Every played Aberdeen fixture in the Cormack era, with the depth the record supports.",
};

export default function MatchesPage() {
  const index = getFixtureIndex();
  if (!index || !index.fixtures.length) {
    return (
      <ContractPage surface="matches" state="empty">
        <section className="page-head" data-contract="matches.hero">
          <p className="eyebrow">Matches</p>
          <h1>Match record</h1>
          <p className="lede">
            No played fixtures are published in this build. Run{" "}
            <code>uv run fitba publish</code> to generate the record.
          </p>
        </section>
      </ContractPage>
    );
  }
  const seasons = Array.from(new Set(index.fixtures.map((row) => row.season))).sort(
    (a, b) => b.localeCompare(a),
  );
  const currentSeason = seasons[0];
  const seasonGroups = seasons.map((season) => ({
    season,
    rows: index.fixtures.filter((row) => row.season === season),
  }));
  return (
    <ContractPage surface="matches">
      <section className="page-head" data-contract="matches.hero">
        <p className="eyebrow">Cormack era</p>
        <h1>Match record</h1>
        <p className="lede">
          Every played Aberdeen fixture, one season at a time, with the score,
          the events, the lineups and the measured stats. The depth label says
          what the feed can show; it is not a claim that the rest does not exist.
        </p>
        <p className="fine-print">
          {index.count} played fixtures.{" "}
          <Link className="text-link" href="/analysis/xg/">
            fxG model and aggregates →
          </Link>{" "}
          <Link className="text-link" href="/analysis/">
            Data analysis →
          </Link>{" "}
          <Link className="text-link" href="/matchday/">
            Matchday →
          </Link>{" "}
          <Link className="text-link" href="/history/">
            The Cormack era →
          </Link>
        </p>
      </section>

      <MatchRecordArchive seasons={seasonGroups} current={currentSeason} />
    </ContractPage>
  );
}
