import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Article, Person, Stats } from "../types";

export function useStats() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
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

export function usePeople(since?: string, name?: string) {
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPeople(await api.getPeople({ since, name, limit: 200 }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load people");
    } finally {
      setLoading(false);
    }
  }, [since, name]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { people, loading, error, refresh };
}

export function useArticles(since?: string) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setArticles(await api.getArticles({ since, limit: 100 }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load articles");
    } finally {
      setLoading(false);
    }
  }, [since]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { articles, loading, error, refresh };
}
