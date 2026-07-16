import {describe, expect, it} from "vitest";
import {readFileSync, readdirSync, statSync} from "node:fs";
import {join} from "node:path";
const root=join(import.meta.dirname,"..");
function files(dir:string):string[]{return readdirSync(dir).flatMap(name=>{const path=join(dir,name);if(["node_modules",".next"].includes(name))return[];return statSync(path).isDirectory()?files(path):[path]})}
const source=()=>files(root).filter(path=>!path.includes("package-lock.json")&&!path.includes("/tests/")).map(path=>readFileSync(path,"utf8")).join("\n");
describe("frontend architecture",()=>{
  it("has no obsolete backend selectors",()=>expect(source()).not.toMatch(/127\.0\.0\.1:8000|localhost:8000|DJANGO_UPSTREAM|BACKEND_URL|NEXT_PUBLIC_API_URL|NEXT_PUBLIC_WS_URL/));
  it("uses the fixed server-only origin",()=>expect(readFileSync(join(root,"lib/server/backend.ts"),"utf8")).toContain('export const DJANGO_ORIGIN = "https://jesca.schoolsoft.online"'));
  it("contains feed success, failure, retry and publication refresh states",()=>{const feed=readFileSync(join(root,"components/Feed.tsx"),"utf8");expect(feed).toContain("No posts yet");expect(feed).toContain("Unable to load posts");expect(feed).toContain("jesca:feed-refresh");expect(feed).toContain("Retry")});
  it("disables and cleans the service worker in development",()=>{const pwa=readFileSync(join(root,"components/PwaManager.tsx"),"utf8");expect(pwa).toContain('process.env.NODE_ENV !== "production"');expect(pwa).toContain("unregisterInsightWorkers");expect(pwa).toContain("removeInsightCaches")});
  it("removes chat and exposes notifications",()=>{expect(()=>readFileSync(join(root,"app/chat/page.tsx"),"utf8")).toThrow();expect(readFileSync(join(root,"app/notifications/page.tsx"),"utf8")).toContain("Mark all read")});
  it("keeps mobile navigation fixed above safe areas",()=>{const css=readFileSync(join(root,"components/Shell.module.css"),"utf8");expect(css).toContain("position:fixed");expect(css).toContain("safe-area-inset-bottom")});
  it("contains no right rail, trending, following, or composer prompt",()=>{const text=source();expect(text).not.toMatch(/RightRail|Trending topics|Suggested creators|For You|Share an idea, story, or observation/)});
  it("gates create controls with publishing permission",()=>expect(readFileSync(join(root,"components/AppShell.tsx"),"utf8")).toContain("user?.can_publish"));
});
