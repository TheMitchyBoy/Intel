/** React hooks for fetching Intel API data with loading/error state. */
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ArticlesQuery, type PeopleQuery } from "../api/client";
import type { Article, Person, Stats } from "../types";

export function useStats() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setStats(await api.getStats());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load stats");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { stats, loading, error, refresh };
}

export function usePeople(query: PeopleQuery & { enabled?: boolean } = {}) {
  const { enabled = true, ...params } = query;
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasLoaded = useRef(false);

  const name = params.name;
  const hours = params.hours;
  const since = params.since;
  const review_status = params.review_status;
  const min_confidence = params.min_confidence;

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function load() {
      if (!hasLoaded.current) {
        setLoading(true);
      }
      setError(null);
      try {
        const data = await api.getPeople({ ...params, limit: params.limit ?? 200 });
        if (!cancelled) {
          setPeople(data);
          hasLoaded.current = true;
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load people");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [enabled, name, hours, since, review_status, min_confidence]);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setError(null);
    try {
      setPeople(await api.getPeople({ ...params, limit: params.limit ?? 200 }));
      hasLoaded.current = true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load people");
    } finally {
      setLoading(false);
    }
  }, [enabled, name, hours, since, review_status, min_confidence]);

  return { people, loading, error, refresh };
}

export function useArticles(query: ArticlesQuery & { enabled?: boolean } = {}) {
  const { enabled = true, ...params } = query;
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasLoaded = useRef(false);

  const hours = params.hours;
  const since = params.since;

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function load() {
      if (!hasLoaded.current) {
        setLoading(true);
      }
      setError(null);
      try {
        const data = await api.getArticles({ ...params, limit: params.limit ?? 100 });
        if (!cancelled) {
          setArticles(data);
          hasLoaded.current = true;
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load articles");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [enabled, hours, since]);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setError(null);
    try {
      setArticles(await api.getArticles({ ...params, limit: params.limit ?? 100 }));
      hasLoaded.current = true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load articles");
    } finally {
      setLoading(false);
    }
  }, [enabled, hours, since]);

  return { articles, loading, error, refresh };
}
