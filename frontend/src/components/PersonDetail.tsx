import type { Person } from "../types";
import { formatDate } from "../api/client";

interface Props {
  person: Person | null;
  onClose: () => void;
}

export function PersonDetail({ person, onClose }: Props) {
  if (!person) return null;

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
          <dt>Mentions</dt>
          <dd>{person.mention_count}</dd>
          <dt>Found</dt>
          <dd>{formatDate(person.created_at)}</dd>
          {person.article_title && (
            <>
              <dt>Article</dt>
              <dd>{person.article_title}</dd>
            </>
          )}
          {person.article_summary && (
            <>
              <dt>Summary</dt>
              <dd className="detail-summary">{person.article_summary}</dd>
            </>
          )}
        </dl>
        {person.article_url && (
          <a
            href={person.article_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn--outline"
          >
            Read original article →
          </a>
        )}
      </div>
    </div>
  );
}
