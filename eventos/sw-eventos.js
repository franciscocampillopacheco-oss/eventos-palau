/* Service worker mínimo de Eventos: solo sirve para poder mostrar avisos en el móvil */
self.addEventListener("install",()=>self.skipWaiting());
self.addEventListener("activate",e=>e.waitUntil(self.clients.claim()));
self.addEventListener("notificationclick",e=>{
  e.notification.close();
  e.waitUntil(self.clients.matchAll({type:"window",includeUncontrolled:true}).then(cs=>{
    for(const c of cs){if(c.url.includes("/eventos/")&&"focus" in c)return c.focus();}
    return self.clients.openWindow("./");
  }));
});
