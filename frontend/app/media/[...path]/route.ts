import {NextRequest} from "next/server";
import {DJANGO_ORIGIN} from "@/lib/server/backend";

export const dynamic = "force-dynamic";

async function proxyMedia(request: NextRequest) {
  const target = new URL(`${request.nextUrl.pathname}${request.nextUrl.search}`, DJANGO_ORIGIN);
  try {
    const upstream = await fetch(target, {method: request.method, cache: "no-store", redirect: "manual", signal: AbortSignal.timeout(15_000)});
    const headers = new Headers();
    for (const name of ["content-type", "content-length", "etag", "last-modified", "accept-ranges", "content-range"]) {
      const value = upstream.headers.get(name);
      if (value) headers.set(name, value);
    }
    headers.set("Cache-Control", upstream.ok ? "public, max-age=3600, stale-while-revalidate=86400" : "no-store");
    return new Response(request.method === "HEAD" ? null : upstream.body, {status: upstream.status, headers});
  } catch {
    return Response.json({error: {code: "media_unreachable", message: "Media could not be loaded."}}, {status: 502});
  }
}

export const GET = proxyMedia;
export const HEAD = proxyMedia;
