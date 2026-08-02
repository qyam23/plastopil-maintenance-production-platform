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
