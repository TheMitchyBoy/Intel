import type { Person } from "../types";

function initials(name: string) {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

interface Props {
  person: Person;
  onClick?: () => void;
  compact?: boolean;
}

export function PersonCard({ person, onClick, compact }: Props) {
  return (
    <article className={`person-card${compact ? " person-card--compact" : ""}`} onClick={onClick}>
      <div className="person-avatar">{initials(person.full_name)}</div>
      <div className="person-body">
        <h3 className="person-name">{person.full_name}</h3>
        {person.role_context && <p className="person-role">{person.role_context}</p>}
        {!compact && person.article_title && (
          <p className="person-article">{person.article_title}</p>
        )}
        <div className="person-meta">
          {person.mention_count > 1 && (
            <span className="badge">{person.mention_count} mentions</span>
          )}
        </div>
      </div>
    </article>
  );
}
