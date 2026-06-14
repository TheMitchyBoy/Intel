import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
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

export function usePeople(since?: string, name?: string) {
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasLoaded = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!hasLoaded.current) {
        setLoading(true);
      }
      setError(null);
      try {
        const data = await api.getPeople({ since, name, limit: 200 });
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
  }, [since, name]);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setPeople(await api.getPeople({ since, name, limit: 200 }));
      hasLoaded.current = true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load people");
    } finally {
      setLoading(false);
    }
  }, [since, name]);

  return { people, loading, error, refresh };
}

export function useArticles(since?: string) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasLoaded = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!hasLoaded.current) {
        setLoading(true);
      }
      setError(null);
      try {
        const data = await api.getArticles({ since, limit: 100 });
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
  }, [since]);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setArticles(await api.getArticles({ since, limit: 100 }));
      hasLoaded.current = true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load articles");
    } finally {
      setLoading(false);
    }
  }, [since]);

  return { articles, loading, error, refresh };
}
