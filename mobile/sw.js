// Service worker d'AMENA mobile : rend l'application installable et rapide à ouvrir.
// Seuls les fichiers de l'interface sont mis en cache ; les appels /api/ (questions, réponses,
// analyses) ne le sont JAMAIS, pour ne laisser aucune trace de la conversation sur le téléphone.
const CACHE = "amena-mobile-v6";
const INTERFACE = ["./", "./index.html", "./app.css", "./app.js", "./manifest.webmanifest", "./icones/icone-192.png", "./icones/icone-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(INTERFACE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((cles) => Promise.all(cles.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.pathname.startsWith("/api/")) return;  // réseau uniquement
  if (!url.pathname.startsWith("/mobile/")) return;
  // Réseau d'abord (toujours la dernière version), cache en secours hors connexion.
  e.respondWith(fetch(e.request).then((r) => {
    const copie = r.clone();
    caches.open(CACHE).then((c) => c.put(e.request, copie));
    return r;
  }).catch(() => caches.match(e.request)));
});
