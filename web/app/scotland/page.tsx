import Link from "next/link";
import { getManifest, getTableFiles } from "@/lib/data";

export const metadata = { title: "The Scottish pyramid · fitba" };

export default function ScotlandPage() {
  const tables = getTableFiles();
  const manifest = getManifest();
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Season {manifest?.season ?? "—"}</p>
        <h1>The Scottish pyramid</h1>
        <p className="lede">
          Tables computed from match results, with points deductions applied and recorded.
        </p>
      </section>
      <div className="grid two-col">
        {tables.map((table) => {
          const slug = table.competition_id.split(":")[1];
          return (
            <Link className="card tier-card" key={table.competition_id} href={`/scotland/${slug}/`}>
              <div className="card-head">
                <div>
                  <p className="eyebrow">Tier {table.tier}</p>
                  <h2>{table.competition_name}</h2>
                </div>
                <span className="tier-count">{table.rows.length}</span>
              </div>
              <ol className="mini-table">
                {table.rows.slice(0, 4).map((row) => (
                  <li key={row.team_id}>
                    <span className="mini-pos">{row.position}</span>
                    <span className="mini-team">{row.team_name}</span>
                    <span className="mini-pts">{row.points}</span>
                  </li>
                ))}
              </ol>
              <span className="text-link">Open table →</span>
            </Link>
          );
        })}
      </div>
    </>
  );
}
