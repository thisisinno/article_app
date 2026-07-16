"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getPostShareText, getPostShareUrl } from "@/lib/share";
import { normalizePostMedia, type Post } from "@/lib/types";
import { Avatar } from "./Avatar";
import {
  BookmarkIcon,
  CommentIcon,
  LikeIcon,
  QuoteIcon,
  ShareIcon,
  ViewIcon,
} from "./Icons";
import styles from "./ContentCard.module.css";
import { useApp } from "./AppProvider";
import {
  COMMENTS_UPDATED,
  type CommentsUpdatedDetail,
} from "./comments/comments-events";
import { PostActionsMenu } from "./posts/PostActionsMenu";
import { PostMediaGallery } from "./media/PostMediaGallery";
import { RelativeTime } from "./RelativeTime";
import { QuotedPostPreview } from "./quotes/QuotedPostPreview";
export function ContentCard({
  initial,
  detail = false,
}: {
  initial: Post;
  detail?: boolean;
}) {
  const [p, setPost] = useState(initial),
    [busy, setBusy] = useState(""),
    [feedback, setFeedback] = useState(""),
    ref = useRef<HTMLElement>(null),
    { openComments, openShare, openQuote } = useApp();
  useEffect(() => setPost(initial), [initial]);
  useEffect(() => {
    const update = (event: Event) => {
      const d = (event as CustomEvent<CommentsUpdatedDetail>).detail;
      if (d?.postId === p.id)
        setPost((v) => ({ ...v, counts: { ...v.counts, comments: d.count } }));
    };
    addEventListener(COMMENTS_UPDATED, update);
    return () => removeEventListener(COMMENTS_UPDATED, update);
  }, [p.id]);
  useEffect(() => {
    if (detail || !ref.current) return;
    let timer: number;
    const ob = new IntersectionObserver(
      ([e]) => {
        clearTimeout(timer);
        if (e.isIntersecting && e.intersectionRatio >= 0.5)
          timer = window.setTimeout(
            () =>
              api<{ count: number }>(`/posts/${p.id}/view/`, {
                method: "POST",
                body: "{}",
              })
                .then((x) =>
                  setPost((v) => ({
                    ...v,
                    counts: { ...v.counts, views: x.count },
                  })),
                )
                .catch(() => undefined),
            1000,
          );
      },
      { threshold: 0.5 },
    );
    ob.observe(ref.current);
    return () => {
      clearTimeout(timer);
      ob.disconnect();
    };
  }, [p.id, detail]);
  async function toggle(kind: "like" | "bookmark") {
    if (busy) return;
    const state = kind === "like" ? "liked" : "bookmarked",
      count = kind === "like" ? "likes" : "bookmarks",
      was = p.viewer_state[state],
      previous = p;
    setBusy(kind);
    setPost((v) => ({
      ...v,
      viewer_state: { ...v.viewer_state, [state]: !was },
      counts: {
        ...v.counts,
        [count]: Math.max(0, v.counts[count] + (was ? -1 : 1)),
      },
    }));
    try {
      const x = await api<{ active: boolean; count: number }>(
        `/posts/${p.id}/${kind}/`,
        { method: was ? "DELETE" : "POST" },
      );
      setPost((v) => ({
        ...v,
        viewer_state: { ...v.viewer_state, [state]: x.active },
        counts: { ...v.counts, [count]: x.count },
      }));
    } catch {
      setPost(previous);
      setFeedback("Action could not be completed.");
    } finally {
      setBusy("");
    }
  }
  return (
    <article
      ref={ref}
      className={`${styles.card} ${detail ? styles.detail : ""}`}
    >
      <header>
        <Link href={`/profile/${p.author.username}`}>
          <Avatar user={p.author} size={42} />
        </Link>
        <div className={styles.identity}>
          <Link href={`/profile/${p.author.username}`}>
            <b>
              {p.author.display_name}
              {p.author.verified && (
                <span className={styles.verified} aria-label="Verified">
                  ✓
                </span>
              )}
            </b>
            <span>
              @{p.author.username} · <RelativeTime value={p.published_at}/>
            </span>
          </Link>
        </div>
        {p.viewer_state.can_delete && (
          <PostActionsMenu post={p} detail={detail} />
        )}
      </header>
      <div className={styles.content}>
        {p.category && (
          <Link
            className={styles.category}
            href={`/?category=${p.category.slug}`}
          >
            {p.category.name}
          </Link>
        )}
        <Link href={`/post/${p.id}`} className={styles.body}>
          {p.type === "article" && <h2>{p.title}</h2>}
          <p className={!detail && p.body.length > 400 ? styles.clamp : ""}>
            {p.excerpt && p.type === "article" && !detail ? p.excerpt : p.body}
          </p>
          {!detail && p.body.length > 400 && (
            <span className={styles.read}>Read more</span>
          )}
        </Link>
        {p.quoted_post&&<QuotedPostPreview post={p.quoted_post}/>}<PostMediaGallery
          media={normalizePostMedia(p)}
          postId={p.id}
          author={p.author.display_name}
          detail={detail}
        />
        {feedback && (
          <p className="actionFeedback" role="status">
            {feedback}
          </p>
        )}
        <footer>
          <button
            onClick={(e) =>
              openComments({
                postId: p.id,
                postAuthor: p.author,
                commentCount: p.counts.comments,
                opener: e.currentTarget,
              })
            }
            aria-label="Comments"
          >
            <CommentIcon />
            <span>{p.counts.comments}</span>
          </button>
          <button onClick={()=>openQuote(p)} aria-label="Quote post"><QuoteIcon/><span>{p.counts.quotes}</span></button>
          <button
            className={p.viewer_state.liked ? styles.liked : ""}
            disabled={!!busy}
            onClick={() => void toggle("like")}
            aria-label={p.viewer_state.liked ? "Unlike" : "Like"}
          >
            <LikeIcon fill={p.viewer_state.liked ? "currentColor" : "none"} />
            <span>{p.counts.likes}</span>
          </button>
          <button
            className={p.viewer_state.bookmarked ? styles.bookmarked : ""}
            disabled={!!busy}
            onClick={() => void toggle("bookmark")}
            aria-label={
              p.viewer_state.bookmarked ? "Remove bookmark" : "Bookmark"
            }
          >
            <BookmarkIcon
              fill={p.viewer_state.bookmarked ? "currentColor" : "none"}
            />
            <span>{p.counts.bookmarks}</span>
          </button>
          <span
            className={styles.metric}
            aria-label={`${p.counts.views} views`}
          >
            <ViewIcon />
            <small>{p.counts.views}</small>
          </span>
          <button
            onClick={() =>
              openShare({
                postId: p.id,
                title: p.title || "Jesca Social Work",
                text: getPostShareText(p.title, p.body),
                url: getPostShareUrl(p.id),
                onCount: (count) =>
                  setPost((v) => ({
                    ...v,
                    counts: { ...v.counts, shares: count },
                  })),
              })
            }
            aria-label="Share"
          >
            <ShareIcon />
            <span>{p.counts.shares}</span>
          </button>
        </footer>
      </div>
    </article>
  );
}
