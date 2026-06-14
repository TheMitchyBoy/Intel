import { formatDate } from "../api/client";
import type { Article } from "../types";

interface Props {
  article: Article;
  onClick?: () => void;
}

export function ArticleCard({ article, onClick }: Props) {
  return (
    <article className="article-card" onClick={onClick}>
      <div className="article-header">
        <span className="article-source">{article.source_name}</span>
        <span className="article-date">{formatDate(article.scraped_at)}</span>
      </div>
      <h3 className="article-title">{article.title}</h3>
      {article.summary && <p className="article-summary">{article.summary}</p>}
      {article.people.length > 0 && (
        <div className="article-people">
          {article.people.map((p) => (
            <span key={p.id} className="chip">
              {p.full_name}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
