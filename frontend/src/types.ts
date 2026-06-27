export interface PersonArticle {
  mention_id: number;
  article_id: number;
  title: string | null;
  url: string | null;
  summary: string | null;
  scraped_at: string | null;
  mention_count: number;
  role_context: string | null;
  confidence?: number;
  sources?: string[];
}

export interface Person {
  id: number;
  full_name: string;
  role_context: string | null;
  mention_count: number;
  article_count: number;
  confidence: number;
  sources: string[];
  review_status: "pending" | "confirmed" | "rejected";
  created_at: string | null;
  latest_seen?: string | null;
  article_id: number | null;
  article_title: string | null;
  article_url: string | null;
  article_summary: string | null;
  articles: PersonArticle[];
}

export interface Article {
  id: number;
  source_name: string;
  title: string;
  url: string;
  summary: string | null;
  published_at: string | null;
  scraped_at: string | null;
  region: string | null;
  status: string;
  people: Person[];
}

export interface Stats {
  total_articles: number;
  total_people: number;
  articles_last_24h: number;
  people_last_24h: number;
  pending_review?: number;
}

export interface PipelineResult {
  sources?: number;
  found?: number;
  new?: number;
  people?: number;
  people_updated?: number;
  errors?: { source: string; error: string }[];
  job?: string;
  articles?: number;
  mentions_created?: number;
  mentions_removed?: number;
}

export interface ScrapeTriggerResponse {
  status: string;
  message: string;
  run_id: number | null;
}

export interface ScrapeStatusResponse {
  running: boolean;
  run_id: number | null;
  result: PipelineResult | null;
  error: string | null;
}

export type Tab = "today" | "people" | "review" | "articles";

declare global {
  interface Window {
    __THROUGHLINE_API_KEY__?: string;
  }
}
