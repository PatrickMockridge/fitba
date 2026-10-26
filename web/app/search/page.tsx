import { ContractPage } from "@/components/ContractPage";
import { SiteSearch } from "@/components/SiteSearch";
import { assetPath } from "@/lib/asset-path";
import { getEntityIndex, type ReaderEntity } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/search/" },
  title: "Search the record · fitba",
  description:
    "Find a page, match, current or former player, club, staff member, season or claim in the published Aberdeen record.",
};

export default function SearchPage() {
  const document = getEntityIndex();
  const entities: ReaderEntity[] = (document?.entities ?? []).map((entity) => ({
    entity_id: entity.entity_id,
    type: entity.type,
    name: entity.name,
    aliases: entity.aliases ?? [],
    href: entity.href,
    indexable: entity.indexable,
    search_group: entity.search_group ?? entity.type,
    sitemap: entity.sitemap,
    source_layers: entity.source_layers ?? [],
    league: entity.league ?? null,
    role_family: entity.role_family ?? null,
  }));

  return (
    <ContractPage surface="search">
      <section className="page-head" data-contract="search.hero">
        <p className="eyebrow">Find the record</p>
        <h1>Search fitba</h1>
        <p className="lede">
          A flat index of published pages, matches, players, clubs, staff, seasons and
          claims. Results link to the existing record; they are not a ranking, a target
          list or a new player profile.
        </p>
        <p className="fine-print">
          Scouted players are a separate lazy-loaded group. The search does not track
          queries, rank results by popularity or use your history.
        </p>
        <div className="hero-actions">
          <a className="button button-ghost" href="/">
            Home
          </a>
          <a className="button button-ghost" href="/scouting/search/">
            Scouting search
          </a>
          <a className="button button-ghost" href="/metrics/">
            Metrics and audit
          </a>
          <a className="button button-ghost" href="/sources/">
            Sources
          </a>
        </div>
      </section>

      <section className="section" data-contract="search.board">
        <SiteSearch
          entities={entities}
          scoutedPath={assetPath("/search/scouted.json")}
        />
      </section>
    </ContractPage>
  );
}
