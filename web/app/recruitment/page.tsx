import Link from "next/link";
import { LegendDisclosure } from "@/components/LegendDisclosure";
import { NeedsBoard } from "@/components/NeedsBoard";
import { PageHeader } from "@/components/PageHeader";
import { getNeeds, getRumours, getTransfers } from "@/lib/data";

export const metadata = { title: "Off the pitch · fitba" };

export default function RecruitmentPage() {
  const needs = getNeeds();
  const transfers = getTransfers();
  const rumours = getRumours();

  const counts = needs?.summary.counts ?? {};
  const strengthen = counts.strengthen ?? 0;
  const none = counts.none ?? 0;
  const known = needs?.summary.availability_known ?? 0;
  const unknown = needs?.summary.availability_unknown ?? 0;
  const profiles = (needs?.families ?? []).filter(
    (family) => family.category !== "none" && family.category !== "unknown",
  ).length;
  const activeRumours = rumours?.summary.by_status.active ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Off the pitch"
        title="Where is the squad short?"
        summary={
          needs
            ? `${strengthen} position groups to strengthen; ${none} are stable. Injury status is unknown for ${known + unknown} players.`
            : "The squad-needs layer is not available for this publish."
        }
      />

      {needs ? <NeedsBoard data={needs} /> : null}

      <section className="grid three-col">
        <article className="card">
          <p className="eyebrow">Transfers</p>
          <h2>Who arrived and who left?</h2>
          <p className="muted">
            {transfers
              ? `${transfers.summary.total} moves · ${transfers.summary.confirmed} officially confirmed`
              : "Register unavailable."}
          </p>
          <Link className="text-link" href="/transfers/">
            Transfer register →
          </Link>
        </article>

        <article className="card">
          <p className="eyebrow">Rumours</p>
          <h2>Is there a sourced link?</h2>
          <p className="muted">
            {activeRumours
              ? `${activeRumours} active link${activeRumours === 1 ? "" : "s"} in the curated register.`
              : "No active, sourced links right now."}
          </p>
          <Link className="text-link" href="/rumours/">
            Rumour mill →
          </Link>
        </article>

        <article className="card">
          <p className="eyebrow">Scouting</p>
          <h2>What profiles matter?</h2>
          <p className="muted">
            {profiles
              ? `${profiles} priority role profiles from the current needs.`
              : "No priority profiles at this publish."}
          </p>
          <Link className="text-link" href="/scouting/">
            Priority profiles →
          </Link>
        </article>
      </section>

      <LegendDisclosure title="What this page does and does not say">
        <p>
          Position profiles and likely market routes only — no named targets, fees
          or wages. Injury status is unknown unless a public team-news source
          confirms it, and unknown entries do not change the model.
        </p>
        <p>
          <Link href="/themes/">Themes</Link> ·{" "}
          <Link href="/methodology/">Method</Link> ·{" "}
          <Link href="/sources/">Sources</Link>
        </p>
      </LegendDisclosure>
    </>
  );
}
