import type { Article } from "../types";
import { formatDate } from "../api/client";

interface Props {
  article: Article | null;
  onClose: () => void;
}

export function ArticleDetail({ article, onClose }: Props) {
  if (!article) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--wide" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <span className="article-source">{article.source_name}</span>
        <h2>{article.title}</h2>
        <p className="modal-meta">
          Scraped {formatDate(article.scraped_at)}
          {article.region && ` · ${article.region}`}
        </p>
        {article.summary && <p className="detail-summary">{article.summary}</p>}
        {article.people.length > 0 && (
          <div className="modal-section">
            <h3>People mentioned</h3>
            <div className="chip-list">
              {article.people.map((p) => (
                <span key={p.id} className="chip chip--large">
                  <strong>{p.full_name}</strong>
                  {p.role_context && <span> — {p.role_context}</span>}
                </span>
              ))}
            </div>
          </div>
        )}
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn--outline"
        >
          Read on Ketchikan Daily News →
        </a>
      </div>
    </div>
  );
}
