"use client";
import {useEffect, useRef, useState} from "react";

async function removeInsightCaches() {
  if (!("caches" in window)) return;
  const names = await caches.keys();
  await Promise.all(names.filter(name => name.startsWith("insight-")).map(name => caches.delete(name)));
}

async function unregisterInsightWorkers() {
  if (!("serviceWorker" in navigator)) return;
  const registrations = await navigator.serviceWorker.getRegistrations();
  await Promise.all(registrations.filter(item => {
    const script = item.active?.scriptURL || item.waiting?.scriptURL || item.installing?.scriptURL || "";
    return new URL(item.scope).origin === location.origin && (!script || script.endsWith("/sw.js"));
  }).map(item => item.unregister()));
}

export function PwaManager() {
  const [offline, setOffline] = useState(false);
  const [update, setUpdate] = useState(false);
  const [error, setError] = useState("");
  const registration = useRef<ServiceWorkerRegistration | null>(null);
  const reloading = useRef(false);
  useEffect(() => {
    setOffline(!navigator.onLine);
    const online = () => setOffline(false), offlineEvent = () => setOffline(true);
    addEventListener("online", online); addEventListener("offline", offlineEvent);
    if (process.env.NODE_ENV !== "production") {
      void Promise.all([unregisterInsightWorkers(), removeInsightCaches()]).catch(() => setError("Cached development data could not be cleared."));
      return () => { removeEventListener("online", online); removeEventListener("offline", offlineEvent); };
    }
    const changed = () => { if (!reloading.current) { reloading.current = true; location.reload(); } };
    navigator.serviceWorker?.addEventListener("controllerchange", changed);
    void navigator.serviceWorker?.register("/sw.js", {updateViaCache: "none"}).then(value => {
      registration.current = value;
      setUpdate(Boolean(value.waiting));
      value.addEventListener("updatefound", () => value.installing?.addEventListener("statechange", () => setUpdate(Boolean(value.waiting))));
    }).catch(() => setError("App update check failed."));
    return () => { removeEventListener("online", online); removeEventListener("offline", offlineEvent); navigator.serviceWorker?.removeEventListener("controllerchange", changed); };
  }, []);
  return <>{offline && <div className="offline">Offline · reconnect to refresh content</div>}{update && <button className="update" onClick={() => registration.current?.waiting?.postMessage("SKIP_WAITING")}>Update available · Reload</button>}{error && <div className="offline">{error}</div>}</>;
}

export async function resetCachedAppData() {
  await Promise.all([unregisterInsightWorkers(), removeInsightCaches()]);
  location.reload();
}
