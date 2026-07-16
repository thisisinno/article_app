const API_BASE = "/api/v1";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const NETWORK_MESSAGE = "The server could not be reached. Check your connection and retry.";
const INVALID_MESSAGE = "The server returned an invalid response. Please retry.";
let csrfToken: string | null = null;
let csrfPromise: Promise<string> | null = null;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status = 0,
    public readonly code = "request_failed",
    public readonly retryable = false,
    public readonly requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiInit = RequestInit & {timeoutMs?: number};

function errorDetails(value: unknown) {
  if (!value || typeof value !== "object" || !("error" in value)) return {};
  const error = (value as {error?: unknown}).error;
  if (typeof error === "string") return {message: error};
  if (!error || typeof error !== "object") return {};
  const item = error as {message?: unknown; code?: unknown; request_id?: unknown};
  return {
    message: typeof item.message === "string" ? item.message : undefined,
    code: typeof item.code === "string" ? item.code : undefined,
    requestId: typeof item.request_id === "string" ? item.request_id : undefined,
  };
}

async function decode<T>(response: Response): Promise<T> {
  const requestId = response.headers.get("X-Request-ID");
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("Content-Type")?.toLowerCase() ?? "";
  if (!contentType.includes("application/json")) {
    throw new ApiError(INVALID_MESSAGE, response.status, "invalid_response", response.status >= 500, requestId);
  }
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new ApiError(INVALID_MESSAGE, response.status, "invalid_response", response.status >= 500, requestId);
  }
  if (!response.ok) {
    const details = errorDetails(value);
    const fallback = response.status === 401 ? "Please sign in to continue." : response.status >= 500 ? "The server is temporarily unavailable. Please retry." : "The request could not be completed.";
    throw new ApiError(details.message || fallback, response.status, details.code || "request_failed", response.status >= 500 || response.status === 429, details.requestId || requestId);
  }
  return value as T;
}

async function request<T>(url: string, init: ApiInit = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort("timeout"), init.timeoutMs ?? 15_000);
  const signal = init.signal ? AbortSignal.any([init.signal, controller.signal]) : controller.signal;
  try {
    const response = await fetch(url, {...init, signal, credentials: "include", cache: "no-store", redirect: "error"});
    return await decode<T>(response);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (init.signal?.aborted) throw new ApiError("The request was cancelled.", 0, "request_aborted", false);
    if (controller.signal.aborted) throw new ApiError("The request timed out. Please retry.", 0, "request_timeout", true);
    throw new ApiError(NETWORK_MESSAGE, 0, "network_error", true);
  } finally {
    clearTimeout(timer);
  }
}

export function clearCsrfToken() {
  csrfToken = null;
  csrfPromise = null;
}

export async function getCsrfToken({forceRefresh = false}: {forceRefresh?: boolean} = {}) {
  if (forceRefresh) clearCsrfToken();
  if (csrfToken) return csrfToken;
  if (!csrfPromise) {
    csrfPromise = request<{csrfToken: string}>(`${API_BASE}/auth/csrf/`).then(data => {
      if (!data?.csrfToken) throw new ApiError(INVALID_MESSAGE, 200, "invalid_response", true);
      csrfToken = data.csrfToken;
      return csrfToken;
    }).finally(() => { csrfPromise = null; });
  }
  return csrfPromise;
}

export function refreshCsrfToken() {
  return getCsrfToken({forceRefresh: true});
}

export async function api<T>(path: string, init: ApiInit = {}, csrfRetried = false): Promise<T> {
  if (!path.startsWith("/") || path.startsWith("//")) throw new ApiError("Invalid API path.", 0, "invalid_path", false);
  const method = init.method?.toUpperCase() || "GET";
  const unsafe = !SAFE_METHODS.has(method);
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (unsafe) headers.set("X-CSRFToken", await getCsrfToken());
  try {
    return await request<T>(`${API_BASE}${path}`, {...init, method, headers});
  } catch (error) {
    if (unsafe && !csrfRetried && error instanceof ApiError && error.status === 403 && error.code === "csrf_failed") {
      headers.set("X-CSRFToken", await refreshCsrfToken());
      return api<T>(path, {...init, method, headers}, true);
    }
    throw error;
  }
}

export function resetAuthCsrf() {
  clearCsrfToken();
}
