import type { HistoryHonour } from "@/lib/data";

const ORDER = [
  "League",
  "Scottish Cup",
  "League Cup",
  "European Cup Winners' Cup",
  "European Super Cup",
];

function label(honour: HistoryHonour) {
  if (honour.competition === "League") return "League title";
  const details = [honour.opponent, honour.score].filter(Boolean).join(" · ");
  return details || honour.competition;
}

export function HonoursCabinet({ honours }: { honours: HistoryHonour[] }) {
  if (!honours.length) {
    return <p className="muted">No honours are published.</p>;
  }
  const grouped = new Map<string, HistoryHonour[]>();
  for (const honour of honours) {
    const key = honour.competition;
    grouped.set(key, [...(grouped.get(key) ?? []), honour]);
  }
  const competitions = [
    ...ORDER.filter((competition) => grouped.has(competition)),
    ...[...grouped.keys()].filter((competition) => !ORDER.includes(competition)),
  ];
  return (
    <div className="honours-grid">
      {competitions.map((competition) => {
        const rows = [...(grouped.get(competition) ?? [])].sort((a, b) =>
          a.season.localeCompare(b.season),
        );
        return (
          <section className="honour-card" key={competition}>
            <div className="honour-head">
              <h3>{competition}</h3>
              <span className="badge badge-neutral">{rows.length}</span>
            </div>
            <ul className="plain-list honour-list">
              {rows.map((honour) => (
                <li key={honour.honour_id}>
                  <span className="honour-season">{honour.season}</span>
                  <span>{label(honour)}</span>
                  <span
                    className={`badge ${
                      honour.era === "cormack" ? "badge-ok" : "badge-neutral"
                    }`}
                  >
                    {honour.era === "cormack" ? "Cormack era" : "Pre-era"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
