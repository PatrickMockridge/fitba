import { PlayerLink } from "@/components/PlayerLink";
import type { NewsArticle } from "@/lib/data";
import { formatDate } from "@/lib/data";

export function NewsGrid({
  articles,
  limit,
}: {
  articles: NewsArticle[];
  limit?: number;
}) {
  const items = limit ? articles.slice(0, limit) : articles;
  if (!items.length) {
    return <p className="muted">No news published yet.</p>;
  }
  return (
    <div className="news-grid">
      {items.map((article) => (
        <div className="news-card" key={article.article_id}>
          <span className="news-category">{article.category}</span>
          <a
            className="news-title"
            href={article.url}
            target="_blank"
            rel="noreferrer"
          >
            {article.title}
          </a>
          <span className="news-meta">
            {article.published_date ? formatDate(article.published_date) : "Undated"} ·{" "}
            afc.co.uk
          </span>
          {article.player_mentions?.length ? (
            <span className="news-mentions">
              Mentioned:{" "}
              {article.player_mentions.map((mention, index) => (
                <span key={mention.href}>
                  {index ? ", " : ""}
                  <PlayerLink name={mention.name} href={mention.href} />
                </span>
              ))}
            </span>
          ) : null}
        </div>
      ))}
    </div>
  );
}
