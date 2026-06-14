import type { Person } from "../types";
import { formatDate } from "../api/client";

interface Props {
  person: Person | null;
  onClose: () => void;
}

export function PersonDetail({ person, onClose }: Props) {
  if (!person) return null;

  const articles = person.articles?.length
    ? person.articles
    : person.article_title
      ? [
          {
            mention_id: person.id,
            article_id: person.article_id ?? 0,
            title: person.article_title,
            url: person.article_url,
            summary: person.article_summary,
            scraped_at: person.created_at,
            mention_count: person.mention_count,
            role_context: person.role_context,
          },
        ]
      : [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <div className="modal-avatar">
          {person.full_name
            .split(" ")
            .map((n) => n[0])
            .join("")
            .slice(0, 2)
            .toUpperCase()}
        </div>
        <h2>{person.full_name}</h2>
        {person.role_context && (
          <p className="modal-role">{person.role_context}</p>
        )}
        <dl className="detail-list">
          <dt>Articles</dt>
          <dd>{person.article_count ?? articles.length}</dd>
          <dt>Total mentions</dt>
          <dd>{person.mention_count}</dd>
          <dt>Latest seen</dt>
          <dd>{formatDate(person.created_at)}</dd>
        </dl>

        {articles.length > 0 && (
          <div className="person-articles">
            <h3>Articles</h3>
            <ul className="person-article-list">
              {articles.map((article) => (
                <li key={`${article.article_id}-${article.mention_id}`} className="person-article-item">
                  <div>
                    <strong>{article.title ?? "Untitled"}</strong>
                    {article.scraped_at && (
                      <span className="person-article-date">{formatDate(article.scraped_at)}</span>
                    )}
                    {article.role_context && (
                      <p className="person-article-role">{article.role_context}</p>
                    )}
                    {article.summary && (
                      <p className="detail-summary">{article.summary}</p>
                    )}
                  </div>
                  {article.url && (
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn--outline btn--small"
                    >
                      Read →
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
