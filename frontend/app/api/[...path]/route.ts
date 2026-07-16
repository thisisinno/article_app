import {NextRequest} from "next/server";
import {DJANGO_ORIGIN} from "@/lib/server/backend";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const HOP_BY_HOP = ["host", "connection", "content-length", "transfer-encoding", "content-encoding", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "upgrade"];

function jsonError(status: number, code: string, message: string, requestId?: string | null) {
  return Response.json({error: {code, message, ...(requestId ? {request_id: requestId} : {})}}, {status, headers: {"Cache-Control": "no-store", ...(requestId ? {"X-Request-ID": requestId} : {})}});
}

const isJson = (value: string | null) => {
  const type = (value ?? "").toLowerCase().split(";", 1)[0].trim();
  return type === "application/json" || type === "application/problem+json";
};

const safePreview = (value: string) => value.slice(0, 200)
  .replace(/(password|cookie|csrf|authorization)(["'\s:=]+)[^\s,;}&<]+/gi, "$1$2[REDACTED]")
  .replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();

async function proxy(request: NextRequest) {
  const target = new URL(`${request.nextUrl.pathname}${request.nextUrl.search}`, DJANGO_ORIGIN);
  const headers = new Headers(request.headers);
  HOP_BY_HOP.forEach(header => headers.delete(header));
  headers.set("Origin", DJANGO_ORIGIN);
  headers.set("Referer", `${DJANGO_ORIGIN}/`);
  headers.set("X-Forwarded-Host", new URL(DJANGO_ORIGIN).host);
  headers.set("X-Forwarded-Proto", "https");
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  const controller = new AbortController();
  const multipart=(request.headers.get("Content-Type")||"").toLowerCase().startsWith("multipart/form-data");
  const hasBody = !["GET", "HEAD"].includes(request.method);
  const timeout = setTimeout(() => controller.abort(), multipart?120_000:hasBody?30_000:15_000);
  try {
    const init: RequestInit & {duplex?: "half"} = {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: controller.signal,
    };
    if (hasBody) init.duplex = "half";
    const upstream = await fetch(target, init);
    const requestId = upstream.headers.get("X-Request-ID") || request.headers.get("X-Request-ID");
    if ([301, 302, 303, 307, 308].includes(upstream.status)) {
      console.error("Unexpected API redirect", {path: target.pathname, status: upstream.status, requestId, location: upstream.headers.get("Location")?.slice(0, 200)});
      return jsonError(502, "unexpected_backend_redirect", "The application server returned an unexpected redirect.", requestId);
    }
    const responseHeaders = new Headers();
    for (const name of ["content-type", "cache-control", "x-request-id", "etag", "last-modified", "content-disposition"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    const cookieHeaders = upstream.headers as Headers & {getSetCookie?: () => string[]};
    const cookies = cookieHeaders.getSetCookie?.() ?? (upstream.headers.get("set-cookie") ? [upstream.headers.get("set-cookie")!] : []);
    cookies.forEach(cookie => responseHeaders.append("Set-Cookie", cookie));
    responseHeaders.set("Cache-Control", "no-store");
    if (request.method === "HEAD" || upstream.status === 204 || upstream.status === 304) {
      return new Response(null, {status: upstream.status, headers: responseHeaders});
    }
    const contentType = upstream.headers.get("Content-Type");
    if (!isJson(contentType)) {
      const preview = safePreview(await upstream.text());
      console.error("Non-JSON API upstream", {path: `${target.pathname}${target.search}`, status: upstream.status, contentType, requestId, preview});
      if ([502, 503, 504].includes(upstream.status)) return jsonError(upstream.status, "backend_gateway_error", "The application server is temporarily unavailable.", requestId);
      if (upstream.status === 200) return jsonError(502, "upstream_non_json", "The application server returned an invalid response.", requestId);
      return jsonError(upstream.status >= 400 ? upstream.status : 502, "upstream_non_json", "The application server failed while processing this request.", requestId);
    }
    return new Response(upstream.body, {status: upstream.status, headers: responseHeaders});
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return jsonError(504, multipart?"upload_timeout":"backend_timeout", multipart?"The upload took too long. Check your connection and retry.":"The application server took too long to respond. Please retry.", request.headers.get("X-Request-ID"));
    }
    return jsonError(502, "backend_unreachable", "The application server could not be reached. Please retry.", request.headers.get("X-Request-ID"));
  } finally {
    clearTimeout(timeout);
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
export const HEAD = proxy;
