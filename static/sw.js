// Service worker minimalista: cacheia só os arquivos estáticos (CSS, ícones, JS).
// Páginas dinâmicas (com sessão/CSRF) sempre vão para a rede — nunca ficam em cache,
// para não vazar estado entre usuários nem servir uma versão velha.
const CACHE = "construir-reformar-static-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((chaves) =>
      Promise.all(chaves.filter((c) => c !== CACHE).map((c) => caches.delete(c)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.pathname.indexOf("/static/") !== 0) {
    return; // deixa passar direto para a rede
  }
  event.respondWith(
    caches.open(CACHE).then((cache) =>
      cache.match(event.request).then(
        (resposta) =>
          resposta ||
          fetch(event.request).then((rede) => {
            cache.put(event.request, rede.clone());
            return rede;
          })
      )
    )
  );
});
