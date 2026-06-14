import type { Article, Person, PipelineResult, Stats } from "../types";

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

export function startOfToday(): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
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

export const api = {
  getStats: () => request<Stats>("/api/v1/stats"),

  getPeople: (params?: { name?: string; since?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.name) q.set("name", params.name);
    if (params?.since) q.set("since", params.since);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<Person[]>(`/api/v1/people${qs ? `?${qs}` : ""}`);
  },

  getPerson: (id: number) => request<Person>(`/api/v1/people/${id}`),

  getArticles: (params?: { source?: string; since?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.source) q.set("source", params.source);
    if (params?.since) q.set("since", params.since);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<Article[]>(`/api/v1/articles${qs ? `?${qs}` : ""}`);
  },

  getArticle: (id: number) => request<Article>(`/api/v1/articles/${id}`),

  triggerScrape: () => request<PipelineResult>("/api/v1/scrape", { method: "POST" }),
};
