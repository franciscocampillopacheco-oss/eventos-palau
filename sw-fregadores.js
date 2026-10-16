// Service worker de Horarios Fregadores: solo sirve para mostrar el aviso de la hora de salida
// y abrir la página al tocarlo. No guarda nada en caché, así los horarios siempre están al día.
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });

self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = new URL('horarios-fregadores.html', self.registration.scope).href;
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (lista) {
      for (var i = 0; i < lista.length; i++) {
        if (lista[i].url.indexOf('horarios-fregadores') >= 0 && 'focus' in lista[i]) return lista[i].focus();
      }
      return self.clients.openWindow(url);
    })
  );
});

// Avisos de turno: el script de Google los manda por Firebase Cloud Messaging.
self.addEventListener('push', function (e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (x) { d = { body: e.data ? e.data.text() : '' }; }
  var m = d.data || d.notification || d;
  e.waitUntil(self.registration.showNotification(m.title || 'Fregadores', {
    body: m.body || '',
    icon: m.icon || 'icono-fregadores-192.png',
    badge: 'icono-fregadores-192.png',
    tag: 'turno-fregadores',
    renotify: true,
    vibrate: [200, 100, 200],
    data: { url: m.url || '' }
  }));
});
