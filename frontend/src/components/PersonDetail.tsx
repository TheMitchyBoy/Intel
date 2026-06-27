/** Person detail modal — view articles, review status, and edit name typos. */
import { useEffect, useState } from "react";
import type { Person } from "../types";
import { formatDate } from "../api/client";

interface Props {
  person: Person | null;
  onClose: () => void;
  onReview?: (status: "confirmed" | "rejected") => void;
  onRename?: (fullName: string) => Promise<void>;
}

export function PersonDetail({ person, onClose, onReview, onRename }: Props) {
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [savingName, setSavingName] = useState(false);

  useEffect(() => {
    if (person) {
      setNameDraft(person.full_name);
      setEditingName(false);
      setRenameError(null);
    }
  }, [person?.id, person?.full_name]);

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
            confidence: person.confidence,
            sources: person.sources,
          },
        ]
      : [];

  const nameChanged = nameDraft.trim() !== person.full_name;

  const handleSaveName = async () => {
    if (!onRename || !nameChanged) return;
    setSavingName(true);
    setRenameError(null);
    try {
      await onRename(nameDraft.trim());
      setEditingName(false);
    } catch (e) {
      setRenameError(e instanceof Error ? e.message : "Failed to save name");
    } finally {
      setSavingName(false);
    }
  };

  const handleCancelEdit = () => {
    setNameDraft(person.full_name);
    setEditingName(false);
    setRenameError(null);
  };

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

        <div className="name-edit">
          {editingName ? (
            <>
              <input
                className="name-edit-input"
                type="text"
                value={nameDraft}
                onChange={(e) => setNameDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleSaveName();
                  if (e.key === "Escape") handleCancelEdit();
                }}
                autoFocus
                disabled={savingName}
              />
              <div className="name-edit-actions">
                <button
                  className="btn btn--primary btn--small"
                  onClick={() => void handleSaveName()}
                  disabled={!nameChanged || !nameDraft.trim() || savingName}
                >
                  {savingName ? "Saving…" : "Save"}
                </button>
                <button
                  className="btn btn--ghost btn--small"
                  onClick={handleCancelEdit}
                  disabled={savingName}
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <div className="name-edit-display">
              <h2>{person.full_name}</h2>
              {onRename && (
                <button
                  className="btn btn--ghost btn--small name-edit-trigger"
                  onClick={() => setEditingName(true)}
                >
                  Edit name
                </button>
              )}
            </div>
          )}
          {renameError && <p className="name-edit-error">{renameError}</p>}
        </div>

        {person.role_context && <p className="modal-role">{person.role_context}</p>}
        <dl className="detail-list">
          <dt>Status</dt>
          <dd>{person.review_status}</dd>
          <dt>Confidence</dt>
          <dd>{Math.round(person.confidence * 100)}%</dd>
          <dt>Sources</dt>
          <dd>{person.sources?.join(", ") || "—"}</dd>
          <dt>Articles</dt>
          <dd>{person.article_count ?? articles.length}</dd>
          <dt>Total mentions</dt>
          <dd>{person.mention_count}</dd>
        </dl>

        {onReview && person.review_status !== "rejected" && (
          <div className="review-actions">
            {person.review_status === "pending" && (
              <button className="btn btn--primary" onClick={() => onReview("confirmed")}>
                Confirm
              </button>
            )}
            <button className="btn btn--ghost" onClick={() => onReview("rejected")}>
              {person.review_status === "confirmed" ? "Reject approved name" : "Reject"}
            </button>
          </div>
        )}

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
                    {article.summary && <p className="detail-summary">{article.summary}</p>}
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
