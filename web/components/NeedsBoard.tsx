import Link from "next/link";
import { MetricStrip } from "@/components/MetricStrip";
import { TableFrame, Th } from "@/components/TableFrame";
import { pct } from "@/lib/format";
import type { NeedsDocument, NeedsFamily } from "@/lib/data";

function anchor(family: NeedsFamily) {
  return family.family.toLowerCase().replaceAll("/", "-");
}

function driverLabel(driver: string) {
  const labels: Record<string, string> = {
    depth_gap: "depth",
    quality_gap: "quality",
    concentration: "concentration",
    family_rating: "rating",
    availability: "availability",
    age: "age",
  };
  return labels[driver] ?? driver.replaceAll("_", " ");
}

function reason(family: NeedsFamily) {
  const measured = family.measured as Record<string, unknown>;
  if (family.category === "strengthen") {
    const drivers = family.drivers.slice(0, 2).map(driverLabel).join(" + ");
    return `${pct(measured.top_share)} top share${drivers ? ` · ${drivers}` : ""}`;
  }
  if (family.category === "cover") {
    return `${String(measured.projected_shortfall ?? "—")} short · ${pct(measured.availability_risk)} availability risk`;
  }
  if (family.category === "replace") return "Outgoing evidence";
  if (family.category === "monitor") return "Watch";
  if (family.category === "unknown") return "Not enough data";
  return "No measured need";
}

function actionLabel(category: string) {
  const labels: Record<string, string> = {
    strengthen: "Strengthen",
    cover: "Cover",
    replace: "Replace",
    monitor: "Monitor",
    none: "No need",
    unknown: "Unknown",
  };
  return labels[category] ?? category;
}

export function NeedsBoard({ data }: { data: NeedsDocument }) {
  const counts = data.summary.counts ?? {};
  const families = [...data.families].sort(
    (a, b) => (a.priority ?? 99) - (b.priority ?? 99),
  );
  const top = families.filter((family) => family.category !== "none").slice(0, 3);
  const known = data.summary.availability_known ?? 0;
  const unknown = data.summary.availability_unknown ?? 0;

  return (
    <section className="section" id="squad-needs">
      <div className="section-head">
        <h2>By position group</h2>
      </div>

      <MetricStrip
        columns={4}
        items={[
          {
            label: "Groups",
            value: data.summary.families ?? families.length,
            note: "measured",
          },
          {
            label: "Strengthen",
            value: counts.strengthen ?? 0,
            note: "structural",
          },
          { label: "No need", value: counts.none ?? 0, note: "stable" },
          {
            label: "Availability known",
            value: `${known}/${known + unknown}`,
            note: "team news",
          },
        ]}
      />

      <TableFrame
        label="Squad needs by position group"
        caption="Aberdeen squad needs by position group"
        className="league-table compact register-table stack-mobile"
      >
        <thead>
          <tr>
            <Th className="num">#</Th>
            <Th>Position group</Th>
            <Th>Action</Th>
            <Th className="num">Available</Th>
            <Th className="num">Top share</Th>
            <Th>Why</Th>
          </tr>
        </thead>
        <tbody>
          {families.map((family) => {
            const measured = family.measured as Record<string, unknown>;
            return (
              <tr key={family.family} id={`needs-${anchor(family)}`}>
                <td className="num" data-label="Priority">
                  {family.priority ?? "—"}
                </td>
                <td className="strong" data-label="Position group">
                  {family.label}
                </td>
                <td data-label="Action">{actionLabel(family.category)}</td>
                <td className="num" data-label="Available">
                  {String(measured.available_players ?? "—")}
                </td>
                <td className="num" data-label="Top share">
                  {pct(measured.top_share)}
                </td>
                <td data-label="Why">{reason(family)}</td>
              </tr>
            );
          })}
        </tbody>
      </TableFrame>

      {top.length ? (
        <details className="page-legend">
          <summary>Evidence for the top {top.length} needs</summary>
          <div className="page-legend-body">
            {top.map((family) => {
              const measured = family.measured as Record<string, unknown>;
              const route = family.market_route ?? {};
              const roster = family.roster_space ?? {};
              return (
                <section key={family.family} className="mini-block">
                  <h3>{family.label}</h3>
                  <p className="muted">
                    {pct(measured.top_share)} top share ·{" "}
                    {String(measured.ready_count ?? "—")} ready ·{" "}
                    {String(roster.current ?? "—")}/
                    {String(roster.max_squad ?? "—")} in the family · route:{" "}
                    {route.primary ?? "none"}
                  </p>
                  <TableFrame
                    label={`${family.label} players`}
                    caption={`${family.label} players and availability`}
                  >
                    <thead>
                      <tr>
                        <Th>Player</Th>
                        <Th className="num">Starts</Th>
                        <Th className="num">Minutes</Th>
                        <Th>Availability</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {family.players.map((player) => (
                        <tr key={`${family.family}-${player.player_id}`}>
                          <td>{player.name ?? "Unknown"}</td>
                          <td className="num">{player.starts ?? 0}</td>
                          <td className="num">{player.minutes ?? 0}</td>
                          <td>{player.availability_status ?? "unknown"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </TableFrame>
                </section>
              );
            })}
            <p>
              <Link href="/scouting/">Priority profiles</Link> ·{" "}
              <Link href="/squad/">Current squad</Link> ·{" "}
              <Link href="/themes/">Themes</Link>
            </p>
          </div>
        </details>
      ) : null}
    </section>
  );
}
