import { PlayerLink } from "@/components/PlayerLink";
import type { ForumSignalFile, RumoursFile } from "@/lib/data";
import { formatDate, formatInteger } from "@/lib/format";

export function FormerPlayerMentions({
  forum,
  rumours,
  limit = 10,
}: {
  forum: ForumSignalFile | null;
  rumours: RumoursFile | null;
  limit?: number;
}) {
  const signals = (forum?.signals ?? [])
    .filter((signal) => signal.affiliation === "former_player")
    .sort((left, right) => right.mentions - left.mentions)
    .slice(0, limit);
  const curated = (rumours?.former_player_mentions ?? []).slice(0, limit);
  if (!signals.length && !curated.length) {
    return (
      <section className="card" data-contract="former.mentions">
        <p className="eyebrow">Fan signal · reference use</p>
        <h2>Former players in the rumour mill</h2>
        <p className="muted">No former-player names were extracted from the sampled topics.</p>
      </section>
    );
  }
  return (
    <section className="card" data-contract="former.mentions">
      <div className="section-head">
        <div>
          <p className="eyebrow">Fan signal · reference use</p>
          <h2>Former players in the rumour mill</h2>
        </div>
        <span className="badge badge-warn">A mention is not a transfer link</span>
      </div>
      <div className="table-wrap">
        <table className="league-table compact">
          <caption className="fine-print">
            Former-player names mentioned in sampled first pages, separate from current squad and external targets.
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Current or last known</th>
              <th scope="col">Rival</th>
              <th className="num" scope="col">Mentions</th>
              <th scope="col">Source</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((signal) => (
              <tr key={signal.player_key ?? signal.player_name}>
                <td>
                  <PlayerLink name={signal.player_name} href={signal.former_href ?? signal.player_href} />
                </td>
                <td>{signal.current_club ?? "—"}</td>
                <td>{signal.at_rival ? signal.rival_club ?? "Rival" : "—"}</td>
                <td className="num">{formatInteger(signal.mentions)}</td>
                <td>Fan signal</td>
              </tr>
            ))}
            {curated.map((row) => (
              <tr key={row.rumour_id}>
                <td>
                  <PlayerLink name={row.player_name} href={row.former_href ?? row.player_href} />
                </td>
                <td>{row.current_club ?? "—"}</td>
                <td>—</td>
                <td className="num">—</td>
                <td>Curated rumour · {row.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        {forum?.coverage.topics_sampled ?? 0} topics and {forum?.coverage.posts_sampled ?? 0} posts sampled on{" "}
        {forum?.sampled_at ? formatDate(forum.sampled_at.slice(0, 10)) : "—"}. No raw posts, usernames or quotes are published.
      </p>
    </section>
  );
}
