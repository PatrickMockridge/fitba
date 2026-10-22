import { BucketBars } from "@/components/BucketBars";
import { PlayerLink } from "@/components/PlayerLink";
import type { ForumSignal, ForumSignalFile, SentimentSummary } from "@/lib/data";
import { formatDate } from "@/lib/format";

const CREDIBILITY_LABEL: Record<string, string> = {
  fan_only: "Fan only",
  club_player: "Aberdeen player",
  cross_referenced_transfer: "Confirmed business",
  cross_referenced_press: "Press cross-ref",
  cross_referenced_club: "Club output cross-ref",
  official_confirmed: "Confirmed rumour",
};

const CREDIBILITY_CLASS: Record<string, string> = {
  fan_only: "badge-neutral",
  club_player: "badge-neutral",
  cross_referenced_transfer: "badge-ok",
  cross_referenced_press: "badge-warn",
  cross_referenced_club: "badge-warn",
  official_confirmed: "badge-ok",
};

function SentimentBars({ label, summary }: { label: string; summary: SentimentSummary }) {
  const positive = summary.positive_share ?? 0;
  const neutral = summary.neutral_share ?? 0;
  const negative = summary.negative_share ?? 0;
  return (
    <div className="sentiment-card">
      <div className="section-head">
        <div>
          <p className="eyebrow">{label}</p>
          <h3>
            {summary.mean === null
              ? "No sample"
              : `${summary.mean > 0 ? "+" : ""}${summary.mean.toFixed(2)} mean`}
          </h3>
        </div>
        <span className="badge badge-neutral">{summary.count} texts</span>
      </div>
      <div className="bar-list">
        <div className="bar-row">
          <span className="bar-label">Positive</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${positive * 100}%` }} />
          </span>
          <span className="bar-value">{Math.round(positive * 100)}%</span>
        </div>
        <div className="bar-row">
          <span className="bar-label">Neutral</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${neutral * 100}%` }} />
          </span>
          <span className="bar-value">{Math.round(neutral * 100)}%</span>
        </div>
        <div className="bar-row">
          <span className="bar-label">Negative</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${negative * 100}%` }} />
          </span>
          <span className="bar-value">{Math.round(negative * 100)}%</span>
        </div>
      </div>
      <p className="fine-print">
        Median {summary.median === null ? "—" : summary.median.toFixed(2)} · rule-based
        VADER compounds.
      </p>
    </div>
  );
}

function SignalRow({ signal }: { signal: ForumSignal }) {
  return (
    <tr>
      <td>
        <strong>
          <PlayerLink name={signal.player_name} href={signal.player_href} />
        </strong>
        {signal.nationality ? <span className="muted"> · {signal.nationality}</span> : null}
      </td>
      <td>{signal.position_group ?? signal.position ?? "—"}</td>
      <td className="num">{signal.age ?? "—"}</td>
      <td className="num">{signal.mentions}</td>
      <td className="num">{signal.topic_count}</td>
      <td>
        <span className={`badge ${CREDIBILITY_CLASS[signal.credibility] ?? "badge-neutral"}`}>
          {CREDIBILITY_LABEL[signal.credibility] ?? signal.credibility}
        </span>
      </td>
      <td className="num">
        {signal.sentiment.mean === null
          ? "—"
          : `${signal.sentiment.mean > 0 ? "+" : ""}${signal.sentiment.mean.toFixed(2)}`}
      </td>
    </tr>
  );
}

export function ForumSignalPanel({
  data,
  limit = 12,
  showSentiment = true,
  showTopics = true,
}: {
  data: ForumSignalFile | null;
  limit?: number;
  showSentiment?: boolean;
  showTopics?: boolean;
}) {
  if (!data) {
    return (
      <div className="card">
        <p className="eyebrow">Fan signal</p>
        <h2>Not ingested yet</h2>
        <p className="muted">
          Run <code>uv run fitba forum</code> and republish to sample the AFC Chat
          Rumour Mill first pages.
        </p>
      </div>
    );
  }

  const signals = data.signals.slice(0, limit);

  return (
    <div className="forum-panel">
      <div className="section-head">
        <div>
          <p className="eyebrow">Fan signal · reference use</p>
          <h2>What the Rumour Mill is talking about</h2>
        </div>
        <div className="hero-actions">
          <span className="badge badge-neutral">{data.coverage.topics_sampled} topics</span>
          <span className="badge badge-neutral">{data.coverage.posts_sampled} posts</span>
          <span className="badge badge-warn">first pages only</span>
        </div>
      </div>

      <p className="lede">
        Names are extracted with a player gazetteer, then labelled by whether the
        same name also appears in the press rumour register, the club&apos;s output
        or confirmed business. A mention is not a transfer link, and a
        cross-reference is not a probability.
      </p>

      {signals.length ? (
        <div className="table-wrap">
          <table className="league-table compact">
            <thead>
              <tr>
                <th>Player mentioned</th>
                <th>Pos</th>
                <th className="num">Age</th>
                <th className="num">Mentions</th>
                <th className="num">Topics</th>
                <th>Cross-reference</th>
                <th className="num">Fan score</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((signal) => (
                <SignalRow key={`${signal.player_name}-${signal.player_key ?? ""}`} signal={signal} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">No player names were extracted from the sampled posts.</p>
      )}

      <p className="fine-print">
        Labels: <strong>Fan only</strong> — no other source;{" "}
        <strong>Aberdeen player</strong> — current squad;{" "}
        <strong>Confirmed business</strong> — in the confirmed register within 550
        days; <strong>Press cross-ref</strong> — a curated press rumour;{" "}
        <strong>Club output cross-ref</strong> — surname appears in AFC news;{" "}
        <strong>Confirmed rumour</strong> — the curated rumour is confirmed.
      </p>

      <div className="grid two-col">
        <BucketBars title="Mentioned positions" buckets={data.profile.position_mix} />
        <BucketBars title="Mentioned age bands" buckets={data.profile.age_mix} />
      </div>
      <p className="fine-print">{data.profile.note}</p>

      <p className="fine-print">
        No raw post bodies, usernames or quotes are published. The forum states{" "}
        <code>{data.source.content_signal}</code>; fitba uses the text as a
        reference signal only and does not train a model on it.
      </p>

      {showSentiment ? (
        <div className="grid three-col">
          <SentimentBars label="Fan forum" summary={data.sentiment.forum} />
          <SentimentBars label="Press rumour claims" summary={data.sentiment.press} />
          <SentimentBars label="Club output" summary={data.sentiment.club} />
        </div>
      ) : null}

      {showSentiment ? <p className="fine-print">{data.sentiment.note}</p> : null}

      {showTopics && data.topics.length ? (
        <div className="mini-block">
          <p className="eyebrow">Sampled topics</p>
          <ul className="plain-list">
            {data.topics.map((topic) => (
              <li key={topic.url}>
                <a href={topic.url} target="_blank" rel="noreferrer">
                  {topic.title}
                </a>
                <span className="muted">
                  {" "}
                  · {topic.sampled_posts} posts sampled
                  {topic.latest_post ? ` · latest ${formatDate(topic.latest_post.slice(0, 10))}` : ""}
                </span>
                {topic.player_mentions?.length ? (
                  <span className="fine-print">
                    {" · "}
                    {topic.player_mentions.map((mention, index) => (
                      <span key={mention.href}>
                        {index ? ", " : ""}
                        <PlayerLink name={mention.name} href={mention.href} />
                      </span>
                    ))}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="fine-print">{data.coverage.note}</p>
    </div>
  );
}
