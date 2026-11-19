self.addEventListener('install', event => { event.waitUntil(self.skipWaiting()); });
self.addEventListener('activate', event => { event.waitUntil(clients.claim()); });
// Never cache authenticated reports or personal data. Offline reporting is not enabled.
self.addEventListener('fetch', event => {
  if (event.request.mode !== 'navigate' || event.request.method !== 'GET') return;
  event.respondWith(fetch(event.request).catch(() => new Response('<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PLASTOPIL</title><body style="font:18px Arial;padding:24px;color:#10283e"><h1>אין חיבור לאינטרנט</h1><p>התחברו לרשת ונסו שוב. דיווחים אינם נשלחים ללא חיבור.</p><button onclick="location.reload()">נסו שוב</button></body></html>', {headers:{'Content-Type':'text/html; charset=utf-8'}})));
});
self.addEventListener('push', event => {
  const payload = event.data ? event.data.json() : {};
  event.waitUntil(self.registration.showNotification(payload.title || 'PLASTOPIL', {
    body: payload.body || 'יש עדכון לקריאה שלך.', tag: payload.tag || 'plastopil-update', renotify: true,
    data: { url: payload.url || '/' },
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url));
});
