import { notFound } from "next/navigation";
import Link from "next/link";
import { LeagueTable } from "@/components/LeagueTable";
import { getTable, getTableFiles } from "@/lib/data";

export const dynamicParams = false;

export function generateStaticParams() {
  return getTableFiles().map((table) => ({
    tier: table.competition_id.split(":")[1],
  }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ tier: string }>;
}) {
  const { tier } = await params;
  const table = getTable(tier);
  const name = table?.rows[0]?.competition_name ?? "Scottish league";
  const title = `${name} table · fitba`;
  const description = `The computed ${name} table with points deductions, cutoffs and form.`;
  return {
    title,
    description,
    alternates: { canonical: `/scotland/${tier}/` },
    openGraph: { title, description, type: "website" },
  };
}

export default async function TierPage({ params }: { params: Promise<{ tier: string }> }) {
  const { tier } = await params;
  const table = getTable(tier);
  if (!table) notFound();

  const deductions = table.rows.filter((row) => row.deduction > 0);
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Tier {table.tier} · Season {table.season}</p>
        <h1>{table.competition_name}</h1>
        <p className="lede">
          {/* The table is computed, not scraped. */}
          {table.rows.length} clubs · results computed from the match feed.
        </p>
      </section>

      <section className="card">
        <LeagueTable
          rows={table.rows}
          highlightTeamId="sco:aberdeen"
          cutoffs={table.cutoffs}
        />
        <div className="table-notes">
          {table.qualification_note ? <p>{table.qualification_note}</p> : null}
          <p>
            P/W/D/L/GF/GA/GD are computed from results. Form is the last five league
            matches, most recent first. Points deductions are shown beside the club and
            included in the points column.
          </p>
          {deductions.length ? (
            <p>
              Deductions applied:{" "}
              {deductions
                .map((row) => `${row.team_name} −${row.deduction}`)
                .join("; ")}
              .
            </p>
          ) : null}
        </div>
      </section>

      <p className="back-link">
        <Link href="/scotland/">← All tiers</Link>
      </p>
    </>
  );
}
