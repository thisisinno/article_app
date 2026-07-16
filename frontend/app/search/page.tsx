"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import type { Post } from "@/lib/types";
import { ContentCard } from "@/components/ContentCard";
import { SearchIcon } from "@/components/Icons";
import { SearchSkeleton } from "@/components/skeletons/Skeletons";
import { CategoryTabs } from "@/components/categories/CategoryTabs";
import styles from "./search.module.css";
const tabs = ["top", "latest", "posts", "articles"];
type Result = { posts: Post[] };
export default function Search() {
  const sp = useSearchParams(),
    router = useRouter(),
    [q, setQ] = useState(sp.get("q") || ""),
    [data, setData] = useState<Result>({ posts: [] }),
    [status, setStatus] = useState<"loading" | "ready" | "error">("loading"),
    [message, setMessage] = useState(""),
    [retry, setRetry] = useState(0),
    tab = sp.get("type") || "top",
    category = sp.get("category") || "";
  useEffect(() => {
    const c = new AbortController(),
      timer = setTimeout(() => {
        const p = new URLSearchParams();
        if (q) p.set("q", q);
        if (tab !== "top") p.set("type", tab);
        if (category) p.set("category", category);
        router.replace(p.size ? `/search?${p}` : "/search", { scroll: false });
        setStatus("loading");
        api<Result>(`/search/?${p}`, { signal: c.signal })
          .then((x) => {
            setData(x);
            setStatus("ready");
          })
          .catch((x) => {
            if (!(x instanceof ApiError && x.code === "request_aborted")) {
              setMessage(x instanceof Error ? x.message : "Search failed.");
              setStatus("error");
            }
          });
      }, 300);
    return () => {
      clearTimeout(timer);
      c.abort();
    };
  }, [q, tab, category, retry, router]);
  function setParam(name: string, value: string) {
    const p = new URLSearchParams(sp);
    value && value !== "top" ? p.set(name, value) : p.delete(name);
    router.push(p.size ? `/search?${p}` : "/search");
  }
  return (
    <div className="content" suppressHydrationWarning>
      <header className={styles.header}>
        <label>
          <SearchIcon />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search Jesca Social Work"
            aria-label="Search Jesca Social Work"
            autoComplete="off"
            name="jesca-content-search"
          />
        </label>
      </header>
      <div className="tabs">
        {tabs.map((x) => (
          <button
            className={`tab ${tab === x ? "active" : ""}`}
            onClick={() => setParam("type", x)}
            key={x}
          >
            {x[0].toUpperCase() + x.slice(1)}
          </button>
        ))}
      </div>
      <CategoryTabs
        selected={category}
        onSelect={(value) => setParam("category", value)}
        className={styles.categories}
        selectedClass={styles.active}
      />
      {status === "loading" ? (
        <SearchSkeleton />
      ) : status === "error" ? (
        <div className="error">
          <p>{message}</p>
          <button className="secondary" onClick={() => setRetry((x) => x + 1)}>
            Retry
          </button>
        </div>
      ) : data.posts.length ? (
        data.posts.map((p) => <ContentCard initial={p} key={p.id} />)
      ) : (
        <div className="empty">
          <SearchIcon />
          <h2>No results</h2>
          <p>Try another phrase or category.</p>
        </div>
      )}
    </div>
  );
}
