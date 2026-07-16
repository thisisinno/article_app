"use client";
import { useCategories } from "./CategoriesProvider";
import { CategoryTabsSkeleton } from "@/components/skeletons/Skeletons";
export function CategoryTabs({
  selected,
  onSelect,
  className,
  selectedClass,
}: {
  selected: string;
  onSelect: (slug: string) => void;
  className?: string;
  selectedClass?: string;
}) {
  const { categories, status, refreshCategories } = useCategories();
  if (status === "idle" || status === "loading")
    return <CategoryTabsSkeleton />;
  return (
    <>
      <div className={className}>
        <button
          className={!selected ? selectedClass : ""}
          onClick={() => onSelect("")}
        >
          All
        </button>
        {categories.map((c) => (
          <button
            className={selected === c.slug ? selectedClass : ""}
            onClick={() => onSelect(c.slug)}
            key={c.id}
          >
            {c.name}
          </button>
        ))}
      </div>
      {status === "error" && !categories.length && (
        <div className="categoryUnavailable">
          <span>Categories are temporarily unavailable.</span>
          <button
            className="textButton"
            onClick={() => void refreshCategories()}
          >
            Retry
          </button>
        </div>
      )}
    </>
  );
}
