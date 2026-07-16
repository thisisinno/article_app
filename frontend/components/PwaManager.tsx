"use client";
import {useEffect, useRef, useState} from "react";

export function PwaManager() {
  const [offline, setOffline] = useState(false);
  const [update, setUpdate] = useState(false);
  const [error, setError] = useState("");
  const registration = useRef<ServiceWorkerRegistration | null>(null);
  const reloading = useRef(false);
  useEffect(() => {
    setOffline(!navigator.onLine);
    const online = () => setOffline(false), offlineEvent = () => setOffline(true);
    const changed = () => { if (!reloading.current) { reloading.current = true; location.reload(); } };
    addEventListener("online", online); addEventListener("offline", offlineEvent);
    navigator.serviceWorker?.addEventListener("controllerchange", changed);
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js", {updateViaCache: "none"}).then(value => {
      registration.current = value;
      setUpdate(Boolean(value.waiting));
      value.addEventListener("updatefound", () => value.installing?.addEventListener("statechange", () => setUpdate(Boolean(value.waiting))));
    }).catch(() => setError("App update check failed."));
    return () => { removeEventListener("online", online); removeEventListener("offline", offlineEvent); navigator.serviceWorker?.removeEventListener("controllerchange", changed); };
  }, []);
  const applyUpdate = () => {
    const waiting = registration.current?.waiting;
    if (!waiting) { setError("The update is not ready yet. Please retry shortly."); return; }
    waiting.postMessage("SKIP_WAITING");
  };
  return <>{offline && <div className="offline">Offline · reconnect to refresh content</div>}{update && <button className="update" onClick={applyUpdate}>Update available · Reload</button>}{error && <div className="offline">{error}</div>}</>;
}

export async function resetCachedAppData() {
  const registrations = "serviceWorker" in navigator ? await navigator.serviceWorker.getRegistrations() : [];
  await Promise.all(registrations.filter(item => new URL(item.scope).origin === location.origin).map(item => item.unregister()));
  if ("caches" in window) {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name === "insight-v1" || name.startsWith("insight-")).map(name => caches.delete(name)));
  }
  location.reload();
}
