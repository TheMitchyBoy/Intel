import type { Article, Person, ScrapeStatusResponse, ScrapeTriggerResponse, Stats } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "";
const API_KEY =
  window.__INTEL_API_KEY__ || import.meta.env.VITE_API_KEY || "dev-api-key";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return res.json();
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

export interface PeopleQuery {
  name?: string;
  since?: string;
  hours?: number;
  limit?: number;
}

export interface ArticlesQuery {
  source?: string;
  since?: string;
  hours?: number;
  limit?: number;
}

export const api = {
  getStats: () => request<Stats>("/api/v1/stats"),

  getPeople: (params?: PeopleQuery) => {
    const q = new URLSearchParams();
    if (params?.name) q.set("name", params.name);
    if (params?.since) q.set("since", params.since);
    if (params?.hours) q.set("hours", String(params.hours));
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<Person[]>(`/api/v1/people${qs ? `?${qs}` : ""}`);
  },

  getPerson: (id: number) => request<Person>(`/api/v1/people/${id}`),

  getArticles: (params?: ArticlesQuery) => {
    const q = new URLSearchParams();
    if (params?.source) q.set("source", params.source);
    if (params?.since) q.set("since", params.since);
    if (params?.hours) q.set("hours", String(params.hours));
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<Article[]>(`/api/v1/articles${qs ? `?${qs}` : ""}`);
  },

  getArticle: (id: number) => request<Article>(`/api/v1/articles/${id}`),

  triggerScrape: () =>
    request<ScrapeTriggerResponse>("/api/v1/scrape", { method: "POST" }),

  getScrapeStatus: (runId?: number) => {
    const qs = runId ? `?run_id=${runId}` : "";
    return request<ScrapeStatusResponse>(`/api/v1/scrape/status${qs}`);
  },
};
