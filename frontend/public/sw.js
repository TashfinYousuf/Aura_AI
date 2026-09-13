// FILE: frontend/public/sw.js

self.addEventListener("install", (event) => {
  console.log("⚡ [AURA SERVICE WORKER] Installed successfully.");
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  console.log("⚡ [AURA SERVICE WORKER] Activated.");
  event.waitUntil(self.clients.claim());
});

// Listen for Push Notifications from Backend
self.addEventListener("push", (event) => {
  let data = { title: "Aura", body: "Thinking about you... ✨" };
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: "https://placehold.co/192x192/8b5cf6/ffffff?text=Aura",
    badge: "https://placehold.co/192x192/8b5cf6/ffffff?text=Aura",
    vibrate: [200, 100, 200],
    data: { url: "/" }
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

// Click notification to open app
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === "/" && "focus" in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow("/");
    })
  );
});