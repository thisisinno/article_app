import type { NextConfig } from "next";

const isProduction = process.env.NODE_ENV === "production";
const configuredUpstream = process.env.DJANGO_UPSTREAM;

function djangoUpstream(): string | null {
  if (!configuredUpstream) return isProduction ? null : "https://jesca.schoolsoft.online";
  let url: URL;
  try {
    url = new URL(configuredUpstream);
  } catch {
    throw new Error("DJANGO_UPSTREAM must be an absolute http(s) URL");
  }
  if (!['http:', 'https:'].includes(url.protocol) || url.pathname !== '/' || url.search || url.hash) {
    throw new Error("DJANGO_UPSTREAM must contain only an http(s) origin");
  }
  if (isProduction) {
    throw new Error("DJANGO_UPSTREAM must not be set in production; Nginx routes /api and /media directly to Django");
  }
  return url.origin;
}

const upstream = djangoUpstream();
const nextConfig: NextConfig = {
  images: { remotePatterns: [] },
  skipTrailingSlashRedirect: true,
  async rewrites() {
    if (!upstream) return [];
    return [
      { source: "/api/:path*", destination: `${upstream}/api/:path*` },
      { source: "/media/:path*", destination: `${upstream}/media/:path*` },
    ];
  },
};

export default nextConfig;
