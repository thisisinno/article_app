"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { ApiError, api, validateCategoriesResponse } from "@/lib/api";
import type { Category } from "@/lib/types";
export type CategoriesStatus =
  "idle" | "loading" | "ready" | "refreshing" | "error";
type Value = {
  categories: Category[];
  status: CategoriesStatus;
  error: ApiError | null;
  hasLoadedOnce: boolean;
  refreshCategories: () => Promise<void>;
  ensureCategories: () => Promise<void>;
};
const Context = createContext<Value | null>(null),
  CACHE_KEY = "jesca-categories-cache:v1",
  TTL = 300_000,
  DELAYS = [0, 300, 900];
let inFlight: Promise<Category[]> | null = null;
const transient = (x: unknown) =>
  x instanceof ApiError &&
  ([
    "network_error",
    "request_timeout",
    "backend_timeout",
    "backend_gateway_error",
    "backend_unreachable",
  ].includes(x.code) ||
    [502, 503, 504].includes(x.status));
const wait = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));
export function CategoriesProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [categories, setCategories] = useState<Category[]>([]),
    [status, setStatus] = useState<CategoriesStatus>("idle"),
    [error, setError] = useState<ApiError | null>(null),
    loaded = useRef(false),
    sequence = useRef(0),
    controller = useRef<AbortController | null>(null);
  useEffect(() => {
    try {
      const cached = JSON.parse(sessionStorage.getItem(CACHE_KEY) || "null");
      if (cached && Date.now() - cached.saved_at < TTL) {
        const value = validateCategoriesResponse({ results: cached.results });
        setCategories(value.results);
        loaded.current = true;
        setStatus("ready");
      }
    } catch {
      sessionStorage.removeItem(CACHE_KEY);
    }
  }, []);
  const load = useCallback(
    async (force = false) => {
      if (!force && loaded.current) return;
      const id = ++sequence.current;
      controller.current?.abort();
      const abort = new AbortController();
      controller.current = abort;
      setError(null);
      setStatus(categories.length ? "refreshing" : "loading");
      const request = async () => {
        let last: unknown;
        for (let n = 0; n < DELAYS.length; n++) {
          if (DELAYS[n]) await wait(DELAYS[n]);
          try {
            return validateCategoriesResponse(
              await api<unknown>("/categories/", { signal: abort.signal }),
            ).results;
          } catch (x) {
            last = x;
            if (
              abort.signal.aborted ||
              !transient(x) ||
              n === DELAYS.length - 1
            )
              throw x;
          }
        }
        throw last;
      };
      try {
        inFlight ??= request().finally(() => {
          inFlight = null;
        });
        const results = await inFlight;
        if (id !== sequence.current) return;
        loaded.current = true;
        setCategories(results);
        setError(null);
        setStatus("ready");
        sessionStorage.setItem(
          CACHE_KEY,
          JSON.stringify({ saved_at: Date.now(), results }),
        );
      } catch (x) {
        if (
          id !== sequence.current ||
          abort.signal.aborted ||
          (x instanceof ApiError && x.code === "request_aborted")
        )
          return;
        setError(
          x instanceof ApiError
            ? x
            : new ApiError("Categories could not be loaded."),
        );
        setStatus(categories.length ? "ready" : "error");
      }
    },
    [categories.length],
  );
  const ensure = useCallback(() => load(false), [load]),
    refresh = useCallback(() => load(true), [load]);
  useEffect(() => {
    void ensure();
    return () => controller.current?.abort();
  }, [ensure]);
  return (
    <Context.Provider
      value={{
        categories,
        status,
        error,
        hasLoadedOnce: loaded.current,
        refreshCategories: refresh,
        ensureCategories: ensure,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useCategories() {
  const value = useContext(Context);
  if (!value) throw Error("Missing CategoriesProvider");
  return value;
}
