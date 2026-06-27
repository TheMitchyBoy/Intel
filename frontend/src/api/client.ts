/**
 * HTTP client for the Throughline REST API.
 *
 * Auth: sends X-API-Key from window.__THROUGHLINE_API_KEY__ (injected by the API
 * when serving the built SPA) or VITE_API_KEY in dev. All paths are relative
 * to VITE_API_URL or the current origin.
 */
import type { Article, Person, ScrapeStatusResponse, ScrapeTriggerResponse, Stats } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "";
const API_KEY =
  window.__THROUGHLINE_API_KEY__ || import.meta.env.VITE_API_KEY || "dev-api-key";

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
    let message = text || `Request failed: ${res.status}`;
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      }
    } catch {
      // keep raw text
    }
    throw new Error(message);
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
  review_status?: string;
  min_confidence?: number;
}

export interface BulkReviewResult {
  updated: number;
  not_found: number[];
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
    if (params?.review_status) q.set("review_status", params.review_status);
    if (params?.min_confidence != null) q.set("min_confidence", String(params.min_confidence));
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

  reviewPerson: (id: number, status: "confirmed" | "rejected" | "pending") =>
    request<Person>(`/api/v1/people/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  renamePerson: (id: number, fullName: string) =>
    request<Person>(`/api/v1/people/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ full_name: fullName }),
    }),

  bulkReviewPeople: (ids: number[], status: "confirmed" | "rejected" | "pending") =>
    request<BulkReviewResult>("/api/v1/people/review/bulk", {
      method: "POST",
      body: JSON.stringify({ ids, status }),
    }),

  triggerReprocess: () =>
    request<ScrapeTriggerResponse>("/api/v1/reprocess/names", { method: "POST" }),

  getReprocessStatus: (runId?: number) => {
    const qs = runId ? `?run_id=${runId}` : "";
    return request<ScrapeStatusResponse>(`/api/v1/reprocess/status${qs}`);
  },

  triggerScrape: () =>
    request<ScrapeTriggerResponse>("/api/v1/scrape", { method: "POST" }),

  getScrapeStatus: (runId?: number) => {
    const qs = runId ? `?run_id=${runId}` : "";
    return request<ScrapeStatusResponse>(`/api/v1/scrape/status${qs}`);
  },
};
