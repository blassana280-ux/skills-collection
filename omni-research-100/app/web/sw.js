/* Service worker : met en cache UNIQUEMENT la coquille statique.
   Les réponses /api/* ne sont JAMAIS mises en cache : aucune donnée périmée
   ni fictive n'est présentée à l'utilisateur. */
'use strict';
const SHELL = ['/', '/index.html', '/app.js', '/styles.css',
               '/manifest.webmanifest', '/icon.svg'];
const CACHE = 'or100-shell-v1';

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
  )).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.pathname.startsWith('/api/')) {
    return; // réseau uniquement
  }
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/')));
    return;
  }
  event.respondWith(caches.match(event.request).then((cached) =>
    cached || fetch(event.request)));
});
