document.addEventListener('DOMContentLoaded', () => {
  const panel = document.querySelector('#push-panel');
  const button = document.querySelector('#enable-push');
  const status = document.querySelector('#push-status');
  if (!panel || !button || !status) return;

  const identity = () => JSON.parse(localStorage.getItem('plastopil_reporter') || 'null');
  const supported = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  const setStatus = text => { status.textContent = text; };
  const refresh = () => {
    const reporter = identity();
    panel.hidden = !reporter?.device_id;
    if (!supported()) { button.hidden = true; setStatus('המכשיר או הדפדפן אינם תומכים בהתראות.'); return; }
    if (Notification.permission === 'granted') { button.hidden = true; setStatus('התראות פעילות במכשיר זה.'); }
    else if (Notification.permission === 'denied') { button.hidden = true; setStatus('התראות נחסמו בהגדרות הדפדפן.'); }
  };
  const keyBytes = value => Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(value.length / 4) * 4, '=')), char => char.charCodeAt(0));

  button.addEventListener('click', async () => {
    const reporter = identity();
    if (!reporter?.device_id || !supported()) return;
    button.disabled = true; setStatus('מבקשים אישור להתראות…');
    try {
      const config = await fetch('/api/push/config').then(response => response.ok ? response.json() : Promise.reject());
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') throw new Error('permission');
      const registration = await navigator.serviceWorker.register('/service-worker.js');
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(config.public_key) });
      const response = await fetch('/api/push-subscriptions', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({device_id: reporter.device_id, subscription}) });
      if (!response.ok) throw new Error('subscription');
      button.hidden = true; setStatus('התראות פעילות במכשיר זה.');
    } catch (error) {
      button.disabled = false;
      setStatus(error.message === 'permission' ? 'לא אושרו התראות. אפשר לאשר אותן מאוחר יותר דרך הגדרות הדפדפן.' : 'לא הצלחנו להפעיל התראות. נסו שוב.');
    }
  });
  window.addEventListener('plastopil:identity-updated', refresh);
  refresh();
});
