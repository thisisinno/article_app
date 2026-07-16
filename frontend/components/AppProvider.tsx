"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  api,
  clearCsrfToken,
  refreshCsrfToken,
  validateAuthResponse,
} from "@/lib/api";
import type { Post, User } from "@/lib/types";
import { QuotedPostPreview } from "./quotes/QuotedPostPreview";
import { useCategories } from "./categories/CategoriesProvider";
import { Avatar } from "./Avatar";
import {
  CloseIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ImageIcon,
} from "./Icons";
import { CommentsSheet, type CommentsTarget } from "./comments/CommentsSheet";
import { ShareSheet, type ShareTarget } from "./sheets/ShareSheet";
import { unsubscribeFromPush } from "@/lib/push";
export type AuthStatus = "loading" | "authenticated" | "anonymous" | "error";
type Ctx = {
  user: User | null;
  authStatus: AuthStatus;
  authOpen: boolean;
  composerOpen: boolean;
  unread: number;
  setUnreadCount: (n: number) => void;
  commentsTarget: CommentsTarget | null;
  openComments: (x: CommentsTarget) => void;
  closeComments: () => void;
  openShare: (x: ShareTarget) => void;
  closeShare: () => void;
  openAuth: () => void;
  openComposer: () => void;
  openQuote: (post: Post) => void;
  close: () => void;
  refresh: () => Promise<User | null>;
  refreshUnread: () => Promise<void>;
  logout: () => Promise<void>;
  toast: (x: string) => void;
};
const Context = createContext<Ctx | null>(null);
export function useApp() {
  const v = useContext(Context);
  if (!v) throw Error("Missing AppProvider");
  return v;
}
export function AppProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter(),
    [user, setUser] = useState<User | null>(null),
    [authStatus, setAuthStatus] = useState<AuthStatus>("loading"),
    [authOpen, setAuth] = useState(false),
    [composerOpen, setComposer] = useState(false),
    [commentsTarget, setCommentsTarget] = useState<CommentsTarget | null>(null),
    [shareTarget, setShareTarget] = useState<ShareTarget | null>(null),
    [quoteTarget, setQuoteTarget] = useState<Post | null>(null),
    [unread, setUnread] = useState(0),
    [message, setMessage] = useState("");
  const refresh = useCallback(async () => {
    try {
      const x = validateAuthResponse(await api<unknown>("/auth/me/"));
      setUser(x.user);
      setAuthStatus(x.user ? "authenticated" : "anonymous");
      return x.user;
    } catch {
      setUser(null);
      setAuthStatus("error");
      throw new ApiError(
        "Unable to verify your session.",
        502,
        "session_verification_failed",
        true,
      );
    }
  }, []);
  const refreshUnread = useCallback(async () => {
    if (!user || document.hidden || !navigator.onLine) return;
    try {
      setUnread(
        (await api<{ count: number }>("/notifications/unread-count/")).count,
      );
    } catch {}
  }, [user]);
  useEffect(() => {
    void refresh().catch(() => undefined);
  }, [refresh]);
  useEffect(() => {
    if (!user) {
      setUnread(0);
      return;
    }
    void refreshUnread();
    const timer = setInterval(() => {
      if (!document.hidden && navigator.onLine) void refreshUnread();
    }, 45000);
    const focus = () => void refreshUnread();
    addEventListener("focus", focus);
    addEventListener("jesca:notifications-changed", focus);
    return () => {
      clearInterval(timer);
      removeEventListener("focus", focus);
      removeEventListener("jesca:notifications-changed", focus);
    };
  }, [user, refreshUnread]);
  useEffect(() => {
    const badges = navigator as Navigator & {
      setAppBadge?: (count: number) => Promise<void>;
      clearAppBadge?: () => Promise<void>;
    };
    void (
      unread ? badges.setAppBadge?.(unread) : badges.clearAppBadge?.()
    )?.catch(() => undefined);
  }, [unread]);
  const toast = (x: string) => {
    setMessage(x);
    setTimeout(() => setMessage(""), 2800);
  };
  async function logoutUser() {
    try {
      await unsubscribeFromPush();
    } catch {}
    await api("/auth/logout/", { method: "POST" });
    clearCsrfToken();
    localStorage.removeItem("jesca-profile-draft");
    setUser(null);
    setUnread(0);
    setAuthStatus("anonymous");
    router.push("/");
    toast("You have been logged out");
  }
  const close = () => {
    setAuth(false);
    setComposer(false);
  };
  return (
    <Context.Provider
      value={{
        user,
        authStatus,
        authOpen,
        composerOpen,
        unread,
        setUnreadCount: (n) => setUnread(Math.max(0, n)),
        commentsTarget,
        openComments: setCommentsTarget,
        closeComments: () => setCommentsTarget(null),
        openShare: setShareTarget,
        closeShare: () => setShareTarget(null),
        openAuth: () => setAuth(true),
        openComposer: () =>
          user?.can_publish
            ? setComposer(true)
            : user
              ? undefined
              : setAuth(true),
        openQuote: (post) => (user ? setQuoteTarget(post) : setAuth(true)),
        close,
        refresh,
        refreshUnread,
        logout: logoutUser,
        toast,
      }}
    >
      {children}
      <AuthDialog />
      <ComposerDialog />
      <QuoteComposer
        target={quoteTarget}
        onClose={() => setQuoteTarget(null)}
      />
      <CommentsSheet
        target={commentsTarget}
        onClose={() => setCommentsTarget(null)}
      />
      <ShareSheet target={shareTarget} onClose={() => setShareTarget(null)} />
      {message && (
        <div className="toast" role="status">
          {message}
        </div>
      )}
    </Context.Provider>
  );
}
function QuoteComposer({
  target,
  onClose,
}: {
  target: Post | null;
  onClose: () => void;
}) {
  const { toast } = useApp(),
    [body, setBody] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const key = target ? `jesca-quote-draft:${target.id}` : "";
  useEffect(() => {
    if (target) setBody(localStorage.getItem(key) || "");
  }, [target, key]);
  useEffect(() => {
    if (target) localStorage.setItem(key, body);
  }, [target, key, body]);
  if (!target) return null;
  const current=target;
  async function publish() {
    if (!body.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const value = await api<{ post: Post; quoted_post_quote_count: number }>(
        `/posts/${current.id}/quote/`,
        { method: "POST", body: JSON.stringify({ body }) },
      );
      localStorage.removeItem(key);
      dispatchEvent(
        new CustomEvent("jesca:post-quotes-updated", {
          detail: { postId: current.id, count: value.quoted_post_quote_count },
        }),
      );
      dispatchEvent(new Event("jesca:feed-refresh"));
      setBody("");
      onClose();
      toast("Quote published");
    } catch (x) {
      setError(
        x instanceof Error ? x.message : "Quote could not be published.",
      );
    } finally {
      setBusy(false);
    }
  }
  const preview = target.quoted_post || {
    id: target.id,
    type: target.type,
    title: target.title,
    body_preview: target.body,
    excerpt: target.excerpt,
    author: target.author,
    category: target.category,
    published_at: target.published_at,
    media_preview: target.media[0]
      ? { url: target.media[0].url, alt_text: target.media[0].alt_text }
      : null,
  };
  return (
    <div className="overlay composerOverlay">
      <dialog open className="composerDialog" aria-modal="true">
        <header>
          <button
            className="iconButton"
            onClick={onClose}
            aria-label="Close quote composer"
          >
            <CloseIcon />
          </button>
          <b>Quote post</b>
          <button
            className="primary mobilePublish"
            disabled={busy || !body.trim()}
            onClick={() => void publish()}
          >
            Quote
          </button>
        </header>
        <label>
          Commentary
          <textarea
            autoFocus
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={5000}
            rows={5}
            placeholder="Add your thoughts"
          />
        </label>
        <QuotedPostPreview post={preview} />
        {error && (
          <p className="formError" role="alert">
            {error}
          </p>
        )}
        <footer>
          <span>{body.length}/5,000</span>
          <button
            className="primary desktopPublish"
            disabled={busy || !body.trim()}
            onClick={() => void publish()}
          >
            {busy ? "Publishing…" : "Publish Quote"}
          </button>
        </footer>
      </dialog>
    </div>
  );
}
function AuthDialog() {
  const { authOpen, close, refresh } = useApp();
  const [mode, setMode] = useState<"login" | "register">("login"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  if (!authOpen) return null;
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const loginResult = validateAuthResponse(
        await api<unknown>(`/auth/${mode}/`, {
          method: "POST",
          body: JSON.stringify(
            Object.fromEntries(new FormData(e.currentTarget)),
          ),
        }),
        true,
      );
      clearCsrfToken();
      const verified = await refresh();
      if (!verified || verified.id !== loginResult.user?.id)
        throw new ApiError(
          "Your session could not be verified. Please retry.",
          502,
          "session_verification_failed",
          true,
        );
      await refreshCsrfToken();
      close();
    } catch (x) {
      if (x instanceof ApiError && x.status === 401)
        setError("The username or password is incorrect.");
      else if (x instanceof ApiError && x.code === "csrf_failed")
        setError("Security token expired. Please retry.");
      else if (
        x instanceof ApiError &&
        [
          "server_error",
          "backend_gateway_error",
          "backend_unreachable",
        ].includes(x.code)
      )
        setError(
          "The server could not complete the login request. Please retry.",
        );
      else setError(x instanceof Error ? x.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div
      className="overlay"
      onMouseDown={(e) => e.target === e.currentTarget && !busy && close()}
    >
      <dialog open aria-modal="true">
        <button
          className="dialogClose iconButton"
          onClick={close}
          aria-label="Close"
        >
          <CloseIcon />
        </button>
        <h2>{mode === "login" ? "Welcome back" : "Join Jesca"}</h2>
        <form onSubmit={submit}>
          {mode === "register" && (
            <>
              <label>
                Display name
                <input name="display_name" required />
              </label>
              <label>
                Email
                <input name="email" type="email" required />
              </label>
            </>
          )}
          <label>
            Username
            <input name="username" autoComplete="username" required />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              minLength={mode === "register" ? 8 : undefined}
              required
            />
          </label>
          {error && (
            <p className="formError" role="alert">
              {error}
            </p>
          )}
          <button className="primary" disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>
        </form>
        <button
          className="textButton"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Create an account" : "I already have an account"}
        </button>
      </dialog>
    </div>
  );
}
function ComposerDialog() {
  const { composerOpen, close, user, toast } = useApp();
  const {
    categories,
    status: categoryStatus,
    error: categoryFailure,
    refreshCategories,
  } = useCategories();
  const [type, setType] = useState<"short" | "article">("short"),
    [body, setBody] = useState(""),
    [title, setTitle] = useState(""),
    [excerpt, setExcerpt] = useState(""),
    [category, setCategory] = useState(""),
    [busy, setBusy] = useState(false),
    [publishError, setPublishError] = useState(""),
    [imageError, setImageError] = useState(""),
    [images, setImages] = useState<
      Array<{ file: File; url: string; alt: string }>
    >([]),
    imageInput = useRef<HTMLInputElement>(null),
    imagesRef = useRef(images);
  imagesRef.current = images;
  useEffect(
    () => () =>
      imagesRef.current.forEach((item) => URL.revokeObjectURL(item.url)),
    [],
  );
  useEffect(() => {
    try {
      const d = JSON.parse(localStorage.getItem("jesca-publish-draft") || "{}");
      setBody(d.body || "");
      setTitle(d.title || "");
      setExcerpt(d.excerpt || "");
      setCategory(d.category || "");
      setType(d.type || "short");
    } catch {}
  }, []);
  useEffect(
    () =>
      localStorage.setItem(
        "jesca-publish-draft",
        JSON.stringify({ body, title, excerpt, category, type }),
      ),
    [body, title, excerpt, category, type],
  );
  useEffect(() => {
    if (
      category &&
      categoryStatus === "ready" &&
      !categories.some((c) => c.slug === category)
    )
      setCategory("");
  }, [category, categoryStatus, categories]);
  useEffect(() => {
    if (!composerOpen && imagesRef.current.length) {
      imagesRef.current.forEach((item) => URL.revokeObjectURL(item.url));
      setImages([]);
    }
  }, [composerOpen]);
  if (!composerOpen || !user?.can_publish) return null;
  async function publish() {
    if (!category) {
      setPublishError("Select a category.");
      return;
    }
    setBusy(true);
    setPublishError("");
    const form = new FormData();
    form.set("type", type);
    form.set("body", body);
    form.set("title", title);
    form.set("excerpt", excerpt);
    form.set("category", category);
    images.forEach((item) => {
      form.append("images", item.file);
      form.append("image_alt_texts", item.alt);
    });
    try {
      await api("/posts/", { method: "POST", body: form });
      setBody("");
      setTitle("");
      setExcerpt("");
      setCategory("");
      images.forEach((item) => URL.revokeObjectURL(item.url));
      setImages([]);
      localStorage.removeItem("jesca-publish-draft");
      close();
      dispatchEvent(new Event("jesca:feed-refresh"));
      toast("Published successfully");
    } catch (x) {
      if (x instanceof ApiError && x.code === "invalid_category") {
        setCategory("");
        void refreshCategories();
        setPublishError("Choose an available category and retry.");
      } else
        setPublishError(x instanceof Error ? x.message : "Publishing failed.");
    } finally {
      setBusy(false);
    }
  }
  const valid = body.trim() && category && (type === "short" || title.trim());
  return (
    <div className="overlay composerOverlay">
      <dialog open className="composerDialog" aria-modal="true">
        <header>
          <button
            className="iconButton"
            onClick={close}
            aria-label="Close composer"
          >
            <CloseIcon />
          </button>
          <b>Create</b>
          <button
            className="primary mobilePublish"
            disabled={busy || !valid}
            onClick={() => void publish()}
          >
            Publish
          </button>
        </header>
        <div className="composerAuthor">
          <Avatar user={user} />
          <b>{user.display_name}</b>
        </div>
        <div className="typeSwitch">
          <button
            className={type === "short" ? "active" : ""}
            onClick={() => setType("short")}
          >
            Post
          </button>
          <button
            className={type === "article" ? "active" : ""}
            onClick={() => setType("article")}
          >
            Article
          </button>
        </div>
        <label>
          Category
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            required
            disabled={categoryStatus === "idle" || categoryStatus === "loading"}
          >
            <option value="">
              {categoryStatus === "idle" || categoryStatus === "loading"
                ? "Loading categories…"
                : "Select a category"}
            </option>
            {categories.map((c) => (
              <option value={c.slug} key={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        {categoryFailure && categoryStatus === "error" && (
          <p className="formError">
            Categories could not be loaded.{" "}
            <button
              className="textButton"
              onClick={() => void refreshCategories()}
            >
              Retry
            </button>
          </p>
        )}
        {categoryStatus === "ready" && !categories.length && (
          <p className="formError">
            {user.is_superuser ? (
              <a href="https://jesca.schoolsoft.online/admin/publishing/category/">
                Create a category in Django admin.
              </a>
            ) : (
              "Ask a superuser to create an active category."
            )}
          </p>
        )}
        {type === "article" && (
          <>
            <label>
              Title
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={240}
                required
              />
            </label>
            <label>
              Excerpt <span className="muted">(optional)</span>
              <textarea
                value={excerpt}
                onChange={(e) => setExcerpt(e.target.value)}
                maxLength={400}
                rows={2}
              />
            </label>
          </>
        )}
        <label>
          {type === "article" ? "Article" : "Post"}
          <textarea
            autoFocus
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="What deserves attention?"
            maxLength={30000}
            rows={8}
          />
        </label>
        <input
          ref={imageInput}
          className="srOnly"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          multiple
          onChange={(e) => {
            const selected = [...(e.target.files || [])];
            if (images.length + selected.length > 10) {
              setImageError("Select no more than 10 images.");
              e.target.value = "";
              return;
            }
            if (selected.some((file) => file.size > 5 * 1024 * 1024)) {
              setImageError("Each image must be 5 MB or smaller.");
              e.target.value = "";
              return;
            }
            setImages((current) => [
              ...current,
              ...selected.map((file) => ({
                file,
                url: URL.createObjectURL(file),
                alt: "",
              })),
            ]);
            setImageError("");
            e.target.value = "";
          }}
        />
        <div className="mediaPicker">
          <button
            type="button"
            className="iconButton"
            aria-label="Add images"
            onClick={() => imageInput.current?.click()}
          >
            <ImageIcon />
          </button>
          <span>{images.length}/10 images selected</span>
        </div>
        {images.length > 0 && (
          <div className="imageStrip">
            {images.map((item, index) => (
              <div className="imageThumb" key={item.url}>
                <img src={item.url} alt={`Selected image ${index + 1}`} />
                <b>{index + 1}</b>
                <input
                  aria-label={`Alt text for image ${index + 1}`}
                  placeholder="Alt text"
                  value={item.alt}
                  onChange={(e) =>
                    setImages((current) =>
                      current.map((x, i) =>
                        i === index ? { ...x, alt: e.target.value } : x,
                      ),
                    )
                  }
                />
                <div>
                  <button
                    type="button"
                    aria-label={`Move image ${index + 1} left`}
                    disabled={!index}
                    onClick={() =>
                      setImages((current) => {
                        const next = [...current];
                        [next[index - 1], next[index]] = [
                          next[index],
                          next[index - 1],
                        ];
                        return next;
                      })
                    }
                  >
                    <ChevronLeftIcon />
                  </button>
                  <button
                    type="button"
                    aria-label={`Move image ${index + 1} right`}
                    disabled={index === images.length - 1}
                    onClick={() =>
                      setImages((current) => {
                        const next = [...current];
                        [next[index], next[index + 1]] = [
                          next[index + 1],
                          next[index],
                        ];
                        return next;
                      })
                    }
                  >
                    <ChevronRightIcon />
                  </button>
                  <button
                    type="button"
                    aria-label={`Remove image ${index + 1}`}
                    onClick={() =>
                      setImages((current) => {
                        URL.revokeObjectURL(current[index].url);
                        return current.filter((_, i) => i !== index);
                      })
                    }
                  >
                    <CloseIcon />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <style jsx>{`
          .mediaPicker {
            display: flex;
            align-items: center;
            gap: 10px;
          }
          .imageStrip {
            display: flex;
            gap: 10px;
            overflow-x: auto;
            padding: 8px 0;
          }
          .imageThumb {
            flex: 0 0 150px;
            position: relative;
          }
          .imageThumb > img {
            width: 150px;
            height: 120px;
            object-fit: cover;
            border-radius: 12px;
          }
          .imageThumb > b {
            position: absolute;
            top: 5px;
            left: 5px;
            background: #111b;
            color: #fff;
            border-radius: 99px;
            padding: 2px 7px;
          }
          .imageThumb > input {
            font-size: 13px !important;
            padding: 7px !important;
          }
          .imageThumb > div {
            display: flex;
            justify-content: center;
          }
          .imageThumb button {
            border: 0;
            background: none;
            padding: 5px;
          }
          .imageThumb svg {
            width: 18px;
          }
        `}</style>
        {imageError && (
          <p className="formError" role="alert">
            {imageError}
          </p>
        )}
        {publishError && (
          <p className="formError" role="alert">
            {publishError}
          </p>
        )}
        <footer>
          <span>{body.length.toLocaleString()}/30,000</span>
          <button
            className="primary desktopPublish"
            disabled={busy || !valid}
            onClick={() => void publish()}
          >
            {busy ? "Publishing…" : "Publish"}
          </button>
        </footer>
      </dialog>
    </div>
  );
}
