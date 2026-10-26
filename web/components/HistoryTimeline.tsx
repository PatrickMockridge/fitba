import type { HistoryHonour, HistoryPerson } from "@/lib/data";

function eventDate(value: string | null | undefined, precision?: string | null) {
  if (!value) return "—";
  if (precision === "year" || value.length === 4) return value;
  if (precision === "month" || value.length === 7) {
    const [year, month] = value.split("-");
    const name = new Date(Number(year), Number(month) - 1, 1).toLocaleString(
      "en-GB",
      { month: "short" },
    );
    return `${name} ${year}`;
  }
  const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      });
}

type TimelineEvent = {
  date: string;
  sort: string;
  kind: "staff" | "honour";
  title: string;
  detail: string;
  badge?: string;
  href?: string;
  anchor?: string;
};

export function HistoryTimeline({
  staff,
  honours,
  eraStart = "2019-12-16",
}: {
  staff: HistoryPerson[];
  honours: HistoryHonour[];
  eraStart?: string;
}) {
  const events: TimelineEvent[] = [];
  const anchored = new Set<string>();
  for (const person of staff) {
    for (const stint of person.stints) {
      const overlapsEra =
        stint.start >= eraStart ||
        stint.end === null ||
        stint.end >= eraStart;
      if (!overlapsEra) continue;
      const startedBeforeEra = stint.start < eraStart;
      events.push({
        date: eventDate(
          startedBeforeEra ? eraStart : stint.start,
          startedBeforeEra ? "day" : stint.start_precision,
        ),
        sort: startedBeforeEra ? eraStart : stint.start,
        kind: "staff",
        title: person.name,
        detail: `${stint.role}${stint.interim ? " · interim" : ""}${
          startedBeforeEra ? " · in post at era start" : ""
        }`,
        badge: stint.end === null ? "In post" : startedBeforeEra ? "In post at start" : "Appointed",
        href: stint.source_urls?.[0],
        anchor: anchored.has(person.person_id)
          ? undefined
          : `staff-${person.person_id}`,
      });
      anchored.add(person.person_id);
      if (stint.end) {
        events.push({
          date: eventDate(stint.end, stint.end_precision),
          sort: stint.end,
          kind: "staff",
          title: person.name,
          detail: `${stint.role} · ${stint.reason_out ?? "left"}`,
          badge: "Departed",
          href: stint.source_urls?.[0],
        });
      }
    }
  }
  for (const honour of honours) {
    if (honour.era !== "cormack") continue;
    events.push({
      date: eventDate(honour.date, honour.date_precision),
      sort: honour.date ?? `${honour.season}-01-01`,
      kind: "honour",
      title: honour.competition,
      detail: `${honour.season}${honour.opponent ? ` · ${honour.opponent}` : ""}${
        honour.score ? ` · ${honour.score}` : ""
      }${honour.penalties ? ` · ${honour.penalties}` : ""}`,
      badge: "Honour",
      href: honour.source_urls?.[0],
    });
  }
  events.sort((a, b) => a.sort.localeCompare(b.sort));
  if (!events.length) {
    return <p className="muted">No era timeline events are published.</p>;
  }
  return (
    <ol className="history-timeline">
      {events.map((event, index) => (
        <li
          className="timeline-item"
          id={event.anchor}
          key={`${event.kind}-${event.sort}-${event.title}-${index}`}
        >
          <span className={`timeline-dot timeline-dot-${event.kind}`} aria-hidden="true" />
          <div className="timeline-body">
            <div className="timeline-meta">
              <span className="timeline-date">{event.date}</span>
              {event.badge ? <span className="badge badge-neutral">{event.badge}</span> : null}
            </div>
            <strong>{event.title}</strong>
            <span className="timeline-detail">{event.detail}</span>
            {event.href ? (
              <a className="fine-print" href={event.href} target="_blank" rel="noreferrer">
                source
              </a>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
