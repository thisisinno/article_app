import {describe, expect, it} from "vitest";
import {readFileSync, readdirSync, statSync} from "node:fs";
import {join} from "node:path";
const root=join(import.meta.dirname,"..");
function files(dir:string):string[]{return readdirSync(dir).flatMap(name=>{const path=join(dir,name);if(["node_modules",".next"].includes(name))return[];return statSync(path).isDirectory()?files(path):[path]})}
const source=()=>files(root).filter(path=>!path.includes("package-lock.json")&&!path.includes("/tests/")).map(path=>readFileSync(path,"utf8")).join("\n");
describe("frontend architecture",()=>{
  it("has no obsolete backend selectors",()=>expect(source()).not.toMatch(/127\.0\.0\.1:8000|localhost:8000|DJANGO_UPSTREAM|BACKEND_URL|NEXT_PUBLIC_API_URL|NEXT_PUBLIC_WS_URL/));
  it("uses the fixed server-only origin",()=>expect(readFileSync(join(root,"lib/server/backend.ts"),"utf8")).toContain('export const DJANGO_ORIGIN = "https://jesca.schoolsoft.online"'));
  it("contains feed success, failure, retry and publication refresh states",()=>{const feed=readFileSync(join(root,"components/Feed.tsx"),"utf8");expect(feed).toContain("No posts yet");expect(feed).toContain("Unable to load posts");expect(feed).toContain("insight:feed-refresh");expect(feed).toContain("Retry")});
  it("disables and cleans the service worker in development",()=>{const pwa=readFileSync(join(root,"components/PwaManager.tsx"),"utf8");expect(pwa).toContain('process.env.NODE_ENV !== "production"');expect(pwa).toContain("unregisterInsightWorkers");expect(pwa).toContain("removeInsightCaches")});
  it("uses a direct Django WebSocket and ticket",()=>{const chat=readFileSync(join(root,"app/chat/page.tsx"),"utf8");expect(chat).toContain('wss://jesca.schoolsoft.online');expect(chat).toContain('/ws/ticket/')});
  it("has mobile navigation and dynamic viewport chat",()=>{expect(readFileSync(join(root,"components/Shell.module.css"),"utf8")).toContain(".mobileNav");expect(readFileSync(join(root,"app/chat/chat.module.css"),"utf8")).toContain("100dvh")});
});
