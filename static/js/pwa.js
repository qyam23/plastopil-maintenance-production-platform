(() => {
  let promptEvent;
  const installed = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const panel = () => document.querySelector('[data-pwa-install]');
  const hint = () => document.querySelector('[data-pwa-hint]');
  const refresh = () => { if (panel()) panel().hidden = installed(); };
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); promptEvent = event; refresh();
  });
  window.addEventListener('appinstalled', () => { promptEvent = null; refresh(); });
  document.addEventListener('DOMContentLoaded', () => {
    if ('serviceWorker' in navigator && window.isSecureContext) navigator.serviceWorker.register('/service-worker.js').catch(() => {});
    refresh();
    document.querySelector('[data-pwa-install-button]')?.addEventListener('click', async () => {
      if (promptEvent) {
        const event = promptEvent; promptEvent = null;
        await event.prompt(); await event.userChoice; refresh(); return;
      }
      const ios = /iPhone|iPad|iPod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
      if (hint()) { hint().hidden = false; hint().textContent = ios ? 'פתחו ב-Safari, לחצו על שיתוף ובחרו ״הוספה למסך הבית״.' : 'פתחו את תפריט הדפדפן ובחרו ״התקנת אפליקציה״ או ״הוספה למסך הבית״, אם האפשרות מופיעה.'; }
    });
  });
})();
