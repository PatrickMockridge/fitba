import Link from "next/link";
import { LeagueTable } from "@/components/LeagueTable";
import { PageProvenance } from "@/components/PageProvenance";
import { getManifest, getTableFiles } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/scotland/" }, title: "The Scottish pyramid · fitba" };

export default function ScotlandPage() {
  const tables = getTableFiles();
  const manifest = getManifest();
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Season {manifest?.season ?? "—"}</p>
        <h1>The full pyramid</h1>
        <p className="lede">
          All four SPFL tiers, computed from results, with promotion, play-off,
          split and relegation cut-offs marked.
        </p>
      </section>

      <div className="pyramid-stack">
        {tables.map((table) => {
          const slug = table.competition_id.split(":")[1];
          return (
            <section className="card" key={table.competition_id}>
              <div className="section-head">
                <div>
                  <p className="eyebrow">Tier {table.tier} · Season {table.season}</p>
                  <h2>{table.competition_name}</h2>
                </div>
                <Link className="text-link" href={`/scotland/${slug}/`}>
                  Open tier →
                </Link>
              </div>
              <LeagueTable
                rows={table.rows}
                highlightTeamId="sco:aberdeen"
                cutoffs={table.cutoffs}
              />
              {table.qualification_note ? (
                <p className="fine-print">{table.qualification_note}</p>
              ) : null}
            </section>
          );
        })}
      </div>

      <p className="fine-print">
        Play-off matches are not included in league tables. Cut-offs follow SPFL rules
        and, for Europe, the current UEFA access list; see the{" "}
        <Link href="/methodology/">methodology</Link> for sources and caveats.
      </p>

      <PageProvenance surface="scotland" />
    </>
  );
}
