/*
 * SERVICE WORKER
 * ==============
 *
 * HISTORICO DESTA CORRECAO (v2)
 * -----------------------------
 * A versao 1 usava "cache primeiro" para TODOS os arquivos, incluindo o
 * index.html. O efeito colateral era grave: depois da primeira visita, o
 * celular passava a servir eternamente a copia guardada e ignorava qualquer
 * republicacao do site. Correcoes publicadas simplesmente nao chegavam ao
 * aparelho, e a unica saida era limpar os dados do site na mao.
 *
 * ESTRATEGIA ATUAL
 * ----------------
 *  - index.html e navegacao -> REDE PRIMEIRO. O app sempre tenta baixar a
 *    versao publicada. O cache so entra em acao quando nao ha internet.
 *  - dados.json            -> REDE PRIMEIRO. Estatistica velha e pior do que
 *    esperar meio segundo a mais.
 *  - icones e manifest     -> CACHE PRIMEIRO. Praticamente nunca mudam.
 *
 * Com isso, publicar uma versao nova passa a bastar: nao e mais necessario
 * lembrar de incrementar a versao do cache a cada deploy. O numero abaixo
 * continua existindo apenas para descartar caches de versoes antigas.
 */
const VERSAO_CACHE = 'fantasy-v20';

// Apenas recursos realmente estaveis entram em cache-first.
const ESTATICOS = [
  './manifest.json',
  './icone-192.png',
  './icone-512.png'
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(VERSAO_CACHE)
      .then((cache) => cache.addAll(ESTATICOS).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((chaves) => Promise.all(
        chaves.filter((c) => c !== VERSAO_CACHE).map((c) => caches.delete(c))
      ))
      .then(() => self.clients.claim())
  );
});

// Permite que a pagina peca a ativacao imediata de uma versao nova.
self.addEventListener('message', (evento) => {
  if (evento.data === 'ATUALIZAR_AGORA') self.skipWaiting();
});

function ehDocumento(req) {
  return req.mode === 'navigate'
      || req.destination === 'document'
      || req.url.endsWith('/')
      || req.url.includes('index.html');
}

self.addEventListener('fetch', (evento) => {
  const req = evento.request;
  if (req.method !== 'GET') return;
  if (!req.url.startsWith(self.location.origin)) return;

  // --- REDE PRIMEIRO: documento e dados ---
  if (ehDocumento(req) || req.url.includes('dados.json') || req.url.includes('hashtag_projecoes_2026_27.json')) {
    evento.respondWith(
      fetch(req)
        .then((resp) => {
          if (resp && resp.status === 200) {
            const copia = resp.clone();
            caches.open(VERSAO_CACHE).then((c) => c.put(req, copia));
          }
          return resp;
        })
        .catch(async () => {
          const cacheado = await caches.match(req);
          if (cacheado) return cacheado;
          if (ehDocumento(req)) return caches.match('./index.html');
          // Nunca devolve HTML para uma requisição JSON. Isso preserva o erro
          // original e permite que a interface mostre uma mensagem coerente.
          return new Response(JSON.stringify({
            erro: 'dados_indisponiveis_offline',
            arquivo: new URL(req.url).pathname.split('/').pop()
          }), {
            status: 503,
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
          });
        })
    );
    return;
  }

  // --- CACHE PRIMEIRO: estaticos ---
  evento.respondWith(
    caches.match(req).then((cacheado) => {
      if (cacheado) return cacheado;
      return fetch(req).then((resp) => {
        if (resp && resp.status === 200 && resp.type === 'basic') {
          const copia = resp.clone();
          caches.open(VERSAO_CACHE).then((c) => c.put(req, copia));
        }
        return resp;
      });
    })
  );
});
