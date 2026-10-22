import Link from "next/link";
import type { NeedsDocument, NeedsFamily } from "@/lib/data";

function anchor(family: string) {
  return family.toLowerCase().replaceAll("/", "-");
}

function Profile({ family }: { family: NeedsFamily }) {
  const profile = family.role_profile ?? {};
  const route = family.market_route ?? {};
  return (
    <article className="priority-card" id={`priority-${anchor(family.family)}`}>
      <div className="priority-head">
        <div>
          <p className="eyebrow">
            {family.category.replaceAll("_", " ")} · {family.urgency}
          </p>
          <h3>{family.label}</h3>
        </div>
        <span className="badge badge-neutral">
          {family.scouting_groups.join(" / ") || family.family}
        </span>
      </div>
      <p className="fine-print">
        Role profile only. The shortlist engine is not live; no candidates are
        ranked or named.
      </p>
      <div className="need-grid">
        <div className="mini-block">
          <p className="eyebrow">Profile</p>
          <p>
            Age band:{" "}
            {Array.isArray(profile.age_band)
              ? (profile.age_band as number[]).join("–")
              : "—"}{" "}
            · minutes floor: {String(profile.min_effective_minutes ?? "—")} · coverage:{" "}
            {String(profile.coverage_floor ?? "—")}
          </p>
        </div>
        <div className="mini-block">
          <p className="eyebrow">Key traits</p>
          <p>
            {Array.isArray(profile.key_traits) && profile.key_traits.length
              ? (profile.key_traits as string[]).join(" · ")
              : "—"}
          </p>
        </div>
        <div className="mini-block">
          <p className="eyebrow">Market route</p>
          <p>{route.primary ?? "none"}</p>
          <p className="fine-print">
            {route.alternatives?.length
              ? `Also: ${route.alternatives.join(", ")}. `
              : ""}
            Fee unknown; no target or wage claim.
          </p>
        </div>
      </div>
      <Link className="text-link" href={`/recruitment/#needs-${anchor(family.family)}`}>
        Needs evidence →
      </Link>
    </article>
  );
}

export function PriorityProfiles({ data }: { data: NeedsDocument }) {
  const priorities = data.families.filter((family) =>
    ["cover", "replace", "strengthen"].includes(family.category),
  );
  if (!priorities.length) {
    return (
      <section className="card" id="priority-profiles">
        <p className="eyebrow">Priority profiles</p>
        <h2>No priority role profile at this publish</h2>
        <p className="fine-print">
          The measured depth and availability do not currently produce a cover,
          replace or strengthen classification. The shortlist engine is not live.
        </p>
      </section>
    );
  }
  return (
    <section className="card" id="priority-profiles">
      <div className="section-head">
        <div>
          <p className="eyebrow">Themes → scouting</p>
          <h2>Priority role profiles</h2>
        </div>
        <span className="badge badge-neutral">{priorities.length} profiles</span>
      </div>
      <p>
        What the method would prioritise if a shortlist existed. These are role
        profiles and market routes, not players; the shortlist engine is not live.
      </p>
      <div className="priority-grid">
        {priorities.map((family) => (
          <Profile family={family} key={family.family} />
        ))}
      </div>
    </section>
  );
}
