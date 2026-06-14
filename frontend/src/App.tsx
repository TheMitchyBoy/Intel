import { useState } from "react";
import { api } from "./api/client";
import { useArticles, usePeople, useStats } from "./hooks/useData";
import type { Article, Person, Tab } from "./types";
import { StatsCards } from "./components/StatsCards";
import { PersonCard } from "./components/PersonCard";
import { ArticleCard } from "./components/ArticleCard";
import { PersonDetail } from "./components/PersonDetail";
import { ArticleDetail } from "./components/ArticleDetail";
import { SetupBanner } from "./components/SetupBanner";

function todayLabel() {
  return new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function App() {
  const [tab, setTab] = useState<Tab>("today");
  const [search, setSearch] = useState("");
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState<string | null>(null);

  const { stats, loading: statsLoading, refresh: refreshStats } = useStats();
  const {
    people: todayPeople,
    loading: todayLoading,
    refresh: refreshToday,
  } = usePeople({ hours: 24, enabled: tab === "today" });
  const {
    people: allPeople,
    loading: peopleLoading,
    refresh: refreshPeople,
  } = usePeople({ name: search || undefined, enabled: tab === "people" });
  const {
    articles,
    loading: articlesLoading,
    refresh: refreshArticles,
  } = useArticles({ enabled: tab === "articles" });

  const refreshAll = () => {
    refreshStats();
    refreshToday();
    refreshPeople();
    refreshArticles();
  };

  const handleScrape = async () => {
    setScraping(true);
    setScrapeMsg("Starting scrape…");
    try {
      const trigger = await api.triggerScrape();
      if (trigger.status === "already_running") {
        setScrapeMsg(trigger.message);
        return;
      }

      setScrapeMsg("Scraping Ketchikan Daily News… (may take 1–2 minutes)");

      while (true) {
        const status = await api.getScrapeStatus();
        if (!status.running) {
          if (status.error) {
            setScrapeMsg(`Scrape failed: ${status.error}`);
          } else if (status.result) {
            const result = status.result;
            const errNote = result.errors?.length
              ? ` Warnings: ${result.errors.map((e) => `${e.source}: ${e.error}`).join("; ")}.`
              : "";
            setScrapeMsg(
              `Found ${result.found} articles, ${result.new} new, ${result.people} people` +
                (result.people_updated ? ` (${result.people_updated} articles updated).` : ".") +
                errNote
            );
          } else {
            setScrapeMsg("Scrape finished but returned no result.");
          }
          break;
        }
        await new Promise((r) => setTimeout(r, 3000));
        refreshStats();
      }
      refreshAll();
    } catch (e) {
      setScrapeMsg(e instanceof Error ? e.message : "Scrape failed");
    } finally {
      setScraping(false);
    }
  };

  const displayPeople = tab === "today" ? todayPeople : allPeople;
  const peopleLoadingState = tab === "today" ? todayLoading : peopleLoading;

  return (
    <div className="app">
      <header className="header">
        <div className="header-brand">
          <div className="logo">Intel</div>
          <div>
            <h1>Ketchikan Daily News CRM</h1>
            <p className="header-sub">Local newspaper intelligence</p>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn btn--ghost" onClick={refreshAll}>
            Refresh
          </button>
          <button className="btn btn--primary" onClick={handleScrape} disabled={scraping}>
            {scraping ? "Scraping…" : "Run scrape"}
          </button>
        </div>
      </header>

      {scrapeMsg && (
        <div className="toast" onClick={() => setScrapeMsg(null)}>
          {scrapeMsg}
        </div>
      )}

      <main className="main">
        <SetupBanner />
        <StatsCards stats={stats} loading={statsLoading} />

        <nav className="tabs">
          {(
            [
              ["today", "Today's names"],
              ["people", "All people"],
              ["articles", "Articles"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              className={`tab${tab === id ? " tab--active" : ""}`}
              onClick={() => setTab(id)}
            >
              {label}
              {id === "today" && todayPeople.length > 0 && (
                <span className="tab-count">{todayPeople.length}</span>
              )}
            </button>
          ))}
        </nav>

        {tab === "people" && (
          <div className="search-bar">
            <input
              type="search"
              placeholder="Search by name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        )}

        {tab === "today" && (
          <section className="section">
            <div className="section-header">
              <h2>Names in the news</h2>
              <span className="section-date">Last 24 hours · {todayLabel()}</span>
            </div>
            {todayLoading && todayPeople.length === 0 ? (
              <p className="empty">Loading today's names…</p>
            ) : todayPeople.length === 0 ? (
              <div className="empty-state">
                <p>No names found in the last 24 hours.</p>
                <p className="empty-hint">
                  Click <strong>Run scrape</strong> to pull Ketchikan Daily News.
                  {allPeople.length > 0 && (
                    <> Older names are in the <strong>All people</strong> tab.</>
                  )}
                  {!stats?.total_articles && (
                    <> Make sure <code>OPENAI_API_KEY</code> is set on Railway for best results.</>
                  )}
                </p>
              </div>
            ) : (
              <div className="people-grid">
                {todayPeople.map((person) => (
                  <PersonCard
                    key={person.id}
                    person={person}
                    onClick={() => setSelectedPerson(person)}
                  />
                ))}
              </div>
            )}
          </section>
        )}

        {tab === "people" && (
          <section className="section">
            <div className="section-header">
              <h2>All people</h2>
              <span className="section-count">{displayPeople.length} records</span>
            </div>
            {peopleLoadingState && displayPeople.length === 0 ? (
              <p className="empty">Loading…</p>
            ) : displayPeople.length === 0 ? (
              <p className="empty">No people found{search ? ` for "${search}"` : ""}.</p>
            ) : (
              <div className="people-grid">
                {displayPeople.map((person) => (
                  <PersonCard
                    key={person.id}
                    person={person}
                    onClick={() => setSelectedPerson(person)}
                  />
                ))}
              </div>
            )}
          </section>
        )}

        {tab === "articles" && (
          <section className="section">
            <div className="section-header">
              <h2>Recent articles</h2>
              <span className="section-count">{articles.length} articles</span>
            </div>
            {articlesLoading && articles.length === 0 ? (
              <p className="empty">Loading articles…</p>
            ) : articles.length === 0 ? (
              <p className="empty">No articles yet. Run a scrape to get started.</p>
            ) : (
              <div className="article-list">
                {articles.map((article) => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    onClick={() => setSelectedArticle(article)}
                  />
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <PersonDetail person={selectedPerson} onClose={() => setSelectedPerson(null)} />
      <ArticleDetail article={selectedArticle} onClose={() => setSelectedArticle(null)} />
    </div>
  );
}
