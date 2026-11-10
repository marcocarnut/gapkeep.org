// GapKeep site's service worker: the site keeps working offline once
// visited. Pages and files come from the network first (so they are never
// stale), from the cache when there is no network. Nothing but this
// site's own files is ever fetched or kept. Written by tools/build.py.
const VERSION = '__VERSION__';
const CACHE = 'gapkeep-' + VERSION;
const CORE = __CORE__;

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((k) => k.startsWith('gapkeep-') && k !== CACHE).map((k) => caches.delete(k))
  )).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  e.respondWith(
    fetch(req).then((res) => {
      if (res.ok && res.type === 'basic') {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: req.mode === 'navigate' }).then((hit) =>
      hit || (req.mode === 'navigate'
        ? caches.match(url.pathname.startsWith('/pt-br/') ? '/pt-br/404.html' : '/404.html')
        : Response.error())))
  );
});
