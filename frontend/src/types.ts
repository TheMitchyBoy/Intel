export interface Person {
  id: number;
  article_id: number;
  full_name: string;
  role_context: string | null;
  mention_count: number;
  created_at: string | null;
  article_title: string | null;
  article_url: string | null;
  article_summary: string | null;
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
}

export interface PipelineResult {
  sources: number;
  found: number;
  new: number;
  people: number;
  errors: { source: string; error: string }[];
}

export type Tab = "today" | "people" | "articles";

declare global {
  interface Window {
    __INTEL_API_KEY__?: string;
  }
}
