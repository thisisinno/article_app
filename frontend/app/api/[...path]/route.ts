import {NextRequest} from "next/server";
import {DJANGO_ORIGIN} from "@/lib/server/backend";

export const dynamic = "force-dynamic";
const HOP_BY_HOP = ["host", "connection", "content-length", "transfer-encoding", "content-encoding", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "upgrade"];

function jsonError(status: number, code: string, message: string) {
  return Response.json({error: {code, message}}, {status, headers: {"Cache-Control": "no-store"}});
}

async function proxy(request: NextRequest) {
  const target = new URL(`${request.nextUrl.pathname}${request.nextUrl.search}`, DJANGO_ORIGIN);
  const headers = new Headers(request.headers);
  HOP_BY_HOP.forEach(header => headers.delete(header));
  headers.set("Origin", DJANGO_ORIGIN);
  headers.set("Referer", `${DJANGO_ORIGIN}/`);
  headers.set("X-Forwarded-Host", new URL(DJANGO_ORIGIN).host);
  headers.set("X-Forwarded-Proto", "https");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const hasBody = !["GET", "HEAD"].includes(request.method);
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: controller.signal,
    });
    if ([301, 302, 303, 307, 308].includes(upstream.status)) {
      return jsonError(502, "unexpected_backend_redirect", "The application server returned an unexpected redirect. Please retry.");
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
    return new Response(request.method === "HEAD" ? null : upstream.body, {status: upstream.status, headers: responseHeaders});
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return jsonError(504, "backend_timeout", "The application server took too long to respond. Please retry.");
    }
    return jsonError(502, "backend_unreachable", "The application server could not be reached. Please retry.");
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
