"use client";

import { useMemo, useState } from "react";
import { BucketBars } from "@/components/BucketBars";
import { PlayerLink } from "@/components/PlayerLink";
import type { ForumSignal, ForumSignalFile, SentimentSummary } from "@/lib/data";
import { formatDate } from "@/lib/format";

const CREDIBILITY_LABEL: Record<string, string> = {
  fan_only: "Fan only",
  club_player: "Aberdeen player",
  cross_referenced_transfer: "Register cross-ref",
  cross_referenced_press: "Press cross-ref",
  cross_referenced_club: "Club output cross-ref",
  official_confirmed: "Confirmed rumour",
};

const AFFILIATION_LABEL: Record<string, string> = {
  current_squad: "Current squad",
  loan_out: "On loan out",
  current_non_official: "At Aberdeen (not official)",
  former_player: "Former player",
  external_target: "External target",
  unknown: "Unknown",
};

const AFFILIATION_CLASS: Record<string, string> = {
  current_squad: "badge-neutral",
  loan_out: "badge-warn",
  current_non_official: "badge-neutral",
  former_player: "badge-warn",
  external_target: "badge-ok",
  unknown: "badge-neutral",
};

const LOOKUP_LABEL: Record<string, string> = {
  former_player: "Former register",
  scouted_player: "Scouted pool",
  api_match: "API lookup",
  local: "Local",
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
          <PlayerLink
            name={signal.player_name}
            href={signal.player_href ?? signal.former_href}
          />
          {signal.current_club ? (
            <span className="muted"> · {signal.current_club}</span>
          ) : null}
        </strong>
        {signal.nationality ? <span className="muted"> · {signal.nationality}</span> : null}
      </td>
      <td>{signal.position_group ?? signal.position ?? "—"}</td>
      <td className="num">{signal.age ?? "—"}</td>
      <td className="num">{signal.mentions}</td>
      <td className="num">{signal.topic_count}</td>
      <td>
        <span className={`badge ${AFFILIATION_CLASS[signal.affiliation ?? "unknown"] ?? "badge-neutral"}`}>
          {AFFILIATION_LABEL[signal.affiliation ?? "unknown"] ?? "Unknown"}
        </span>
        {signal.at_rival ? <span className="badge badge-warn"> rival</span> : null}
      </td>
      <td>
        {signal.lookup_status ? (
          <span className="badge badge-neutral">
            {LOOKUP_LABEL[signal.lookup_status] ?? signal.lookup_status}
          </span>
        ) : (
          "—"
        )}
      </td>
      <td>
        <span className={`badge ${CREDIBILITY_CLASS[signal.credibility] ?? "badge-neutral"}`}>
          {CREDIBILITY_LABEL[signal.credibility] ?? signal.credibility}
        </span>
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

  const [affiliation, setAffiliation] = useState("all");
  const signals = useMemo(
    () =>
      data.signals
        .filter(
          (signal) =>
            affiliation === "all" || (signal.affiliation ?? "unknown") === affiliation,
        )
        .slice(0, limit),
    [data.signals, affiliation, limit],
  );

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

      <div className="board-controls">
        <label>
          Affiliation
          <select value={affiliation} onChange={(event) => setAffiliation(event.target.value)}>
            <option value="all">All affiliations</option>
            <option value="external_target">External target</option>
            <option value="former_player">Former player</option>
            <option value="current_squad">Current squad</option>
            <option value="loan_out">On loan out</option>
            <option value="current_non_official">At Aberdeen (not official)</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
      </div>

      {signals.length ? (
        <div className="table-wrap">
          <table className="league-table compact">
<caption className="fine-print">Sampled player mentions and cross-reference labels.</caption>
            <thead>
              <tr>
                <th>Player mentioned</th>
                <th>Pos</th>
                <th className="num">Age</th>
                <th className="num">Mentions</th>
                <th className="num">Topics</th>
                <th>Affiliation</th>
                <th>Lookup</th>
                <th>Cross-reference</th>
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
        <strong>Register cross-ref</strong> — in the confirmed register within
        550 days, not a current deal; <strong>Press cross-ref</strong> — a
        curated press rumour;{" "}
        <strong>Club output cross-ref</strong> — surname appears in AFC news;{" "}
        <strong>Confirmed rumour</strong> — the curated rumour is confirmed.
      </p>
      <p className="fine-print">
        Lookup: <strong>Former register</strong> — the name resolves to a
        confirmed former Aberdeen player; <strong>Scouted pool</strong> — the
        name is in the scouted player universe; <strong>API lookup</strong> —
        the name was found in neither, so it was resolved once through the
        provider&apos;s player-profile search. An ambiguous name is not guessed.
      </p>

      <div className="grid two-col">
        <BucketBars
          title="External names mentioned — positions"
          buckets={data.profile.position_mix}
        />
        <BucketBars
          title="External names mentioned — age bands"
          buckets={data.profile.age_mix}
        />
      </div>
      <p className="fine-print">
        {data.profile.note} The table keeps every affiliation; the position and age bars
        count external targets only.
      </p>

      <p className="fine-print">
        No raw post bodies, usernames or quotes are published. The forum states{" "}
        <code>{data.source.content_signal}</code>; fitba uses the text as a
        reference signal only and does not train a model on it.
      </p>

      {showSentiment ? (
        <>
          <p className="fine-print">
            Sampled first-page sentiment across {data.coverage.topics_sampled} topics and{" "}
            {data.coverage.posts_sampled} posts. It is not a poll of the fanbase and
            no score is attached to a named player.
          </p>
          <div className="grid three-col">
            <SentimentBars label="Fan forum" summary={data.sentiment.forum} />
            <SentimentBars label="Press rumour claims" summary={data.sentiment.press} />
            <SentimentBars label="Club output" summary={data.sentiment.club} />
          </div>
        </>
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
