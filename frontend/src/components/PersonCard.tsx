import type { Person } from "../types";

function initials(name: string) {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function confidenceLabel(score: number) {
  if (score >= 0.9) return "High";
  if (score >= 0.75) return "Medium";
  return "Low";
}

interface Props {
  person: Person;
  onClick?: () => void;
  compact?: boolean;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (selected: boolean) => void;
}

export function PersonCard({ person, onClick, compact, selectable, selected, onSelect }: Props) {
  const articleCount = person.article_count ?? person.articles?.length ?? 1;

  return (
    <article
      className={`person-card${compact ? " person-card--compact" : ""}${selected ? " person-card--selected" : ""}`}
      onClick={onClick}
    >
      {selectable && (
        <label className="person-select" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={selected ?? false}
            onChange={(e) => onSelect?.(e.target.checked)}
            aria-label={`Select ${person.full_name}`}
          />
        </label>
      )}
      <div className="person-avatar">{initials(person.full_name)}</div>
      <div className="person-body">
        <h3 className="person-name">{person.full_name}</h3>
        {person.role_context && <p className="person-role">{person.role_context}</p>}
        {!compact && person.article_title && (
          <p className="person-article">
            {articleCount > 1
              ? `${articleCount} articles · latest: ${person.article_title}`
              : person.article_title}
          </p>
        )}
        <div className="person-meta">
          <span className={`badge badge--${person.review_status}`}>{person.review_status}</span>
          <span className="badge badge--confidence">
            {confidenceLabel(person.confidence)} · {Math.round(person.confidence * 100)}%
          </span>
          {articleCount > 1 && <span className="badge">{articleCount} articles</span>}
        </div>
      </div>
    </article>
  );
}
