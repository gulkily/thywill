const CACHE_VERSION = 'v2';
const SHELL_CACHE = `thywill-shell-${CACHE_VERSION}`;
const PRECACHE_ASSETS = [
  '/',
  '/manifest.webmanifest',
  '/static/js/htmx.min.js',
  '/static/js/session-persistence.js',
  '/static/js/offline-data.js',
  '/static/js/prayer-sync.js',
  '/static/logos/logo.svg',
  '/static/favicon.ico',
  '/static/favicon-32.ico',
  '/static/favicon-16.ico'
];

const DB_NAME = 'thywill-offline';
const DB_VERSION = 2;
const MARK_QUEUE_STORE = 'markQueue';

let queueProcessing = false;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(PRECACHE_ASSETS))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key.startsWith('thywill-shell-') && key !== SHELL_CACHE)
          .map((key) => caches.delete(key))
      );

      try {
        await processPrayerQueue();
      } catch (error) {
        console.warn('[PWA] Failed to process prayer queue on activate:', error);
      }

      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return;
  }

  const { request } = event;
  const requestUrl = new URL(request.url);

  if (request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(request));
    return;
  }

  if (requestUrl.origin === self.location.origin) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  if (requestUrl.hostname.includes('cdn.tailwindcss.com')) {
    event.respondWith(cacheFirst(request));
  }
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'thywill-prayer-sync') {
    event.waitUntil(processPrayerQueue());
  }
});

self.addEventListener('message', (event) => {
  if (event.data === 'flushPrayerQueue') {
    event.waitUntil(processPrayerQueue());
  }
});

async function handleNavigationRequest(request) {
  try {
    const networkResponse = await fetch(request);
    const cache = await caches.open(SHELL_CACHE);
    cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch (error) {
    const cache = await caches.open(SHELL_CACHE);
    const exact = await cache.match(request);
    if (exact) {
      return exact;
    }

    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) {
      return cached;
    }

    return cache.match('/');
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(SHELL_CACHE);
  const cached = await cache.match(request);

  const networkFetch = fetch(request)
    .then((response) => {
      if (response && response.status === 200) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);

  return cached || networkFetch;
}

async function cacheFirst(request) {
  const cache = await caches.open(SHELL_CACHE);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request, { mode: 'no-cors' });
    cache.put(request, response.clone());
    return response;
  } catch (error) {
    return cached;
  }
}

function openQueueDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(MARK_QUEUE_STORE)) {
        db.createObjectStore(MARK_QUEUE_STORE, { keyPath: 'id' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getQueuedPrayerMarks() {
  const db = await openQueueDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(MARK_QUEUE_STORE, 'readonly');
    const store = tx.objectStore(MARK_QUEUE_STORE);
    const request = store.getAll();

    request.onsuccess = () => {
      const records = request.result || [];
      records.sort((a, b) => {
        const aTime = Date.parse(a.createdAt || 0);
        const bTime = Date.parse(b.createdAt || 0);
        return aTime - bTime;
      });
      resolve(records);
    };

    request.onerror = () => reject(request.error);
  });
}

async function removeQueuedPrayerMark(id) {
  const db = await openQueueDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(MARK_QUEUE_STORE, 'readwrite');
    const store = tx.objectStore(MARK_QUEUE_STORE);
    const request = store.delete(id);

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function sendQueuedPrayerMark(record) {
  const url = record.url || `/mark/${record.prayerId}`;
  const absoluteUrl = new URL(url, self.location.origin).toString();

  const response = await fetch(absoluteUrl, {
    method: record.method || 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/html',
      'HX-Request': 'true',
      'X-Thywill-Offline': 'background'
    },
    body: JSON.stringify({ prayed_at: record.prayedAt }),
    credentials: 'include'
  });

  if (!response.ok) {
    throw new Error('Failed to sync queued prayer mark');
  }

  const html = await response.text();

  return { html };
}

async function processPrayerQueue() {
  if (queueProcessing) {
    return;
  }

  queueProcessing = true;
  try {
    const records = await getQueuedPrayerMarks();
    for (const record of records) {
      try {
        const result = await sendQueuedPrayerMark(record);
        await removeQueuedPrayerMark(record.id);
        await broadcastPrayerSync({
          type: 'offline-prayer-sync',
          prayerId: record.prayerId,
          html: result.html,
          metadata: record.metadata || {}
        });
      } catch (error) {
        console.warn('[PWA] Prayer mark sync failed, will retry later:', error);
        break;
      }
    }
  } catch (error) {
    console.error('[PWA] Unable to process prayer queue:', error);
  } finally {
    queueProcessing = false;
  }
}

async function broadcastPrayerSync(payload) {
  try {
    const clientList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    clientList.forEach((client) => {
      client.postMessage(payload);
    });
  } catch (error) {
    console.warn('[PWA] Failed to broadcast prayer sync result:', error);
  }
}
