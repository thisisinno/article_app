"use client";
import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Feed } from "@/components/Feed";
import { CategoryTabs } from "@/components/categories/CategoryTabs";
import { useCategories } from "@/components/categories/CategoriesProvider";
import styles from "./page.module.css";
export default function Home() {
  const sp = useSearchParams(),
    router = useRouter(),
    category = sp.get("category") || "",
    { categories, hasLoadedOnce } = useCategories();
  function select(slug: string) {
    const q = new URLSearchParams(sp);
    slug ? q.set("category", slug) : q.delete("category");
    router.replace(q.size ? `/?${q}` : "/", { scroll: false });
  }
  useEffect(() => {
    if (
      hasLoadedOnce &&
      category &&
      !categories.some((x) => x.slug === category)
    )
      select("");
  }, [categories, category, hasLoadedOnce]);
  return (
    <div className="content">
      <header className={`pageHeader ${styles.premiumHeader}`}>
        <span />
        <h1 className={styles.brandTitle}>
          <i className={styles.brandMark} />
          Jesca Social Work
        </h1>
        <span />
      </header>
      <CategoryTabs
        selected={category}
        onSelect={select}
        className={styles.categories}
        selectedClass={styles.selected}
      />
      <Feed
        path={`/feed/${category ? `?category=${encodeURIComponent(category)}` : ""}`}
      />
    </div>
  );
}
