import type { Stats } from "../types";

interface Props {
  stats: Stats | null;
  loading: boolean;
}

export function StatsCards({ stats, loading }: Props) {
  const cards = [
    { label: "Names today", value: stats?.people_last_24h, accent: true },
    { label: "Articles today", value: stats?.articles_last_24h },
    { label: "Total people", value: stats?.total_people },
    { label: "Total articles", value: stats?.total_articles },
  ];

  return (
    <div className="stats-grid">
      {cards.map((card) => (
        <div key={card.label} className={`stat-card${card.accent ? " stat-card--accent" : ""}`}>
          <span className="stat-label">{card.label}</span>
          <span className="stat-value">{loading ? "…" : (card.value ?? 0)}</span>
        </div>
      ))}
    </div>
  );
}
