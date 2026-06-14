import { useState } from "react";
import { api } from "./api/client";
import { useArticles, usePeople, useStats } from "./hooks/useData";
import type { Article, Person, PipelineResult, Tab } from "./types";
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

async function pollJobStatus(
  getStatus: (runId?: number) => Promise<{ running: boolean; result?: PipelineResult | null; error?: string | null }>,
  runId: number | undefined,
  onTick?: () => void
): Promise<{ ok: boolean; result?: PipelineResult; message: string }> {
  await new Promise((r) => setTimeout(r, 500));

  for (let i = 0; i < 120; i++) {
    const status = await getStatus(runId);
    if (!status.running) {
      if (status.error) {
        return { ok: false, message: status.error };
      }
      if (status.result) {
        return { ok: true, result: status.result, message: "" };
      }
      return { ok: false, message: "Job finished but returned no result — check Railway logs." };
    }
    if (i % 2 === 0) onTick?.();
    await new Promise((r) => setTimeout(r, 2000));
  }
  return { ok: false, message: "Timed out waiting for job to finish." };
}

export default function App() {
  const [tab, setTab] = useState<Tab>("today");
  const [search, setSearch] = useState("");
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [scraping, setScraping] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
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
  } = usePeople({
    name: search || undefined,
    min_confidence: highConfidenceOnly ? 0.75 : undefined,
    enabled: tab === "people",
  });
  const {
    people: reviewPeople,
    loading: reviewLoading,
    refresh: refreshReview,
  } = usePeople({ review_status: "pending", enabled: tab === "review" });
  const {
    articles,
    loading: articlesLoading,
    refresh: refreshArticles,
  } = useArticles({ enabled: tab === "articles", limit: 200 });

  const refreshAll = () => {
    refreshStats();
    refreshToday();
    refreshPeople();
    refreshReview();
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

      const runId = trigger.run_id ?? undefined;
      setScrapeMsg("Scraping Ketchikan Daily News… (usually under 30 seconds)");

      const result = await pollJobStatus(api.getScrapeStatus, runId, refreshStats);
      if (!result.ok) {
        setScrapeMsg(`Scrape failed: ${result.message}`);
      } else if (result.result) {
        const parsed = result.result;
        const errNote = parsed.errors?.length
          ? ` Warnings: ${parsed.errors.map((e) => `${e.source}: ${e.error}`).join("; ")}.`
          : "";
        setScrapeMsg(
          `Found ${parsed.found ?? 0} articles, ${parsed.new ?? 0} new, ${parsed.people ?? 0} people` +
            (parsed.people_updated ? ` (${parsed.people_updated} articles updated).` : ".") +
            errNote
        );
      } else {
        setScrapeMsg("Scrape completed.");
      }
      refreshAll();
    } catch (e) {
      setScrapeMsg(e instanceof Error ? e.message : "Scrape failed");
    } finally {
      setScraping(false);
    }
  };

  const handleReprocess = async () => {
    setReprocessing(true);
    setScrapeMsg("Starting name re-extraction…");
    try {
      const trigger = await api.triggerReprocess();
      if (trigger.status === "already_running") {
        setScrapeMsg(trigger.message);
        return;
      }

      const runId = trigger.run_id ?? undefined;
      setScrapeMsg("Re-extracting names from all articles…");

      const result = await pollJobStatus(api.getReprocessStatus, runId, refreshStats);
      if (!result.ok) {
        setScrapeMsg(`Re-extract failed: ${result.message}`);
      } else if (result.result) {
        const parsed = result.result;
        setScrapeMsg(
          `Re-processed ${parsed.articles ?? 0} articles — ` +
            `${parsed.mentions_created ?? 0} mentions created, ` +
            `${parsed.mentions_removed ?? 0} removed.`
        );
      } else {
        setScrapeMsg("Name re-extraction completed.");
      }
      refreshAll();
    } catch (e) {
      setScrapeMsg(e instanceof Error ? e.message : "Re-extract failed");
    } finally {
      setReprocessing(false);
    }
  };

  const handleReview = async (status: "confirmed" | "rejected") => {
    if (!selectedPerson) return;
    try {
      const updated = await api.reviewPerson(selectedPerson.id, status);
      setSelectedPerson(updated);
      refreshAll();
      setScrapeMsg(
        status === "confirmed"
          ? `Confirmed ${updated.full_name}`
          : `Rejected ${updated.full_name}`
      );
    } catch (e) {
      setScrapeMsg(e instanceof Error ? e.message : "Review failed");
    }
  };

  const displayPeople = tab === "today" ? todayPeople : tab === "review" ? reviewPeople : allPeople;
  const peopleLoadingState =
    tab === "today" ? todayLoading : tab === "review" ? reviewLoading : peopleLoading;
  const busy = scraping || reprocessing;

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
          <button className="btn btn--ghost" onClick={handleReprocess} disabled={busy}>
            {reprocessing ? "Re-extracting…" : "Re-extract names"}
          </button>
          <button className="btn btn--primary" onClick={handleScrape} disabled={busy}>
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
              ["review", "Review queue"],
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
              {id === "review" && (stats?.pending_review ?? reviewPeople.length) > 0 && (
                <span className="tab-count">{stats?.pending_review ?? reviewPeople.length}</span>
              )}
            </button>
          ))}
        </nav>

        {tab === "people" && (
          <div className="filter-bar">
            <div className="search-bar" style={{ marginBottom: 0 }}>
              <input
                type="search"
                placeholder="Search by name…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <label>
              <input
                type="checkbox"
                checked={highConfidenceOnly}
                onChange={(e) => setHighConfidenceOnly(e.target.checked)}
              />
              High confidence only (75%+)
            </label>
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
              <span className="section-count">{displayPeople.length} people</span>
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

        {tab === "review" && (
          <section className="section">
            <div className="section-header">
              <h2>Review queue</h2>
              <span className="section-count">{reviewPeople.length} pending</span>
            </div>
            {reviewLoading && reviewPeople.length === 0 ? (
              <p className="empty">Loading review queue…</p>
            ) : reviewPeople.length === 0 ? (
              <div className="empty-state">
                <p>No names pending review.</p>
                <p className="empty-hint">
                  Names with low confidence or a single source appear here for manual confirmation.
                </p>
              </div>
            ) : (
              <div className="people-grid">
                {reviewPeople.map((person) => (
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

      <PersonDetail
        person={selectedPerson}
        onClose={() => setSelectedPerson(null)}
        onReview={tab === "review" || selectedPerson?.review_status === "pending" ? handleReview : undefined}
      />
      <ArticleDetail article={selectedArticle} onClose={() => setSelectedArticle(null)} />
    </div>
  );
}
