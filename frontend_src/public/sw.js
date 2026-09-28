/* Nexus service worker: lets the app open and your saved reading work without a connection.
 *
 *  - App scripts, styles and icons: cached the first time, served from the cache after.
 *  - Pages: the network first; when offline, the last copy of that page (or a small "you are offline" page).
 *  - Your data and who you are signed in as (session, subjects, materials, notes, answers, questions, progress, saved answers, uploaded files for the viewer):
 *    the network first; when offline, the last copy. Nothing else from the API is ever stored (no login attempts, no search, no quiz
 *    answers, no exports). The data cache is emptied whenever you log in or out (the page asks for that), so another person
 *    using this browser never sees it.
 *  - Changes (saving, asking, quizzes) need a connection and say so; nothing is queued behind your back.
 */
const V = "nexus-v3";
const STATIC = `${V}-static`;
const PAGES = `${V}-pages`;
const DATA = `${V}-data`;
const MAX_DATA = 250;

const CACHEABLE_API = [
  /^\/api\/v1\/session$/,
  /^\/api\/v1\/dashboard$/,
  /^\/api\/v1\/saved$/,
  /^\/api\/v1\/account$/,
  /^\/api\/v1\/subjects$/,
  /^\/api\/v1\/subjects\/\d+$/,
  /^\/api\/v1\/subjects\/\d+\/(materials|notes|questions|mcq|progress|report|flashcards|topics|revision|quiz)$/,
  /^\/api\/v1\/subjects\/\d+\/(materials|notes|questions)\/\d+$/,
  /^\/api\/v1\/subjects\/\d+\/materials\/\d+\/file$/,
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.open(PAGES).then((c) => c.add("/offline")));
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const k of await caches.keys()) if (!k.startsWith(V)) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("message", (event) => {
  if (event.data === "clear-data") event.waitUntil(caches.delete(DATA));
});

async function trim(cache) {
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - MAX_DATA; i++) await cache.delete(keys[i]);
}

async function networkFirst(request, cacheName, fallback) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone()).then(() => (cacheName === DATA ? trim(cache) : null)).catch(() => {});
    }
    return response;
  } catch {
    const hit = await cache.match(request, { ignoreVary: true });
    if (hit) return hit;
    if (fallback) return (await caches.open(PAGES)).match(fallback);
    return new Response(JSON.stringify({ error: { code: "offline", message: "You are offline and this has not been saved on this device yet." } }),
      { status: 503, headers: { "Content-Type": "application/json" } });
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(STATIC);
  const hit = await cache.match(request);
  if (hit) return hit;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone()).catch(() => {});
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  const path = url.pathname;
  if (path.startsWith("/_next/static/") || path.startsWith("/mediapipe/") || path === "/icon.svg" || path === "/manifest.webmanifest" || /^\/logo\./.test(path)) {
    event.respondWith(cacheFirst(request));
  } else if (path.startsWith("/api/")) {
    if (CACHEABLE_API.some((re) => re.test(path)) && !url.search) event.respondWith(networkFirst(request, DATA, null));
  } else if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, PAGES, "/offline"));
  }
});
