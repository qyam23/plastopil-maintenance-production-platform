document.addEventListener('DOMContentLoaded', () => {
  const panel = document.querySelector('#push-panel');
  const button = document.querySelector('#enable-push');
  const status = document.querySelector('#push-status');
  if (!panel || !button || !status) return;

  const identity = () => JSON.parse(localStorage.getItem('plastopil_reporter') || 'null');
  const supported = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  const setStatus = text => { status.textContent = text; };
  const subscriptionStatus = async reporter => {
    const response = await fetch(`/api/push-subscriptions/status?device_id=${encodeURIComponent(reporter.device_id)}`);
    if (!response.ok) throw new Error('status');
    return response.json();
  };
  const refresh = async () => {
    const reporter = identity();
    panel.hidden = !reporter?.device_id;
    if (!supported()) { button.hidden = true; setStatus('המכשיר או הדפדפן אינם תומכים בהתראות.'); return; }
    if (Notification.permission === 'granted') {
      try {
        const state = await subscriptionStatus(reporter);
        if (state.configured && state.subscribed) { button.hidden = true; setStatus('התראות פעילות במכשיר זה.'); }
        else { button.hidden = false; setStatus('אישור הדפדפן קיים, אך המכשיר עדיין לא מחובר להתראות. לחצו להשלמה.'); }
      } catch { button.hidden = false; setStatus('לא ניתן לאמת את חיבור ההתראות. לחצו לנסות שוב.'); }
    }
    else if (Notification.permission === 'denied') { button.hidden = true; setStatus('התראות נחסמו בהגדרות הדפדפן.'); }
    else { button.hidden = false; setStatus('אפשרו התראות כדי לקבל עדכונים על הקריאות שלכם.'); }
  };
  const keyBytes = value => Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(value.length / 4) * 4, '=')), char => char.charCodeAt(0));

  button.addEventListener('click', async () => {
    if (!supported()) return;
    button.disabled = true; setStatus('מבקשים אישור להתראות…');
    try {
      // Reconfirm the browser's device binding immediately before sending the
      // subscription. This repairs identities carried over from an old session.
      if (window.plastopilEnsureReporter && !await window.plastopilEnsureReporter()) throw new Error('identity');
      const reporter = identity();
      if (!reporter?.device_id) throw new Error('identity');
      const config = await fetch('/api/push/config').then(response => response.ok ? response.json() : Promise.reject());
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') throw new Error('permission');
      const registration = await navigator.serviceWorker.register('/service-worker.js');
      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(config.public_key) });
      const response = await fetch('/api/push-subscriptions', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({device_id: reporter.device_id, subscription}) });
      if (!response.ok) throw new Error('subscription');
      button.hidden = true; setStatus('התראות פעילות במכשיר זה.');
    } catch (error) {
      button.disabled = false;
      setStatus(error.message === 'permission' ? 'לא אושרו התראות. אפשר לאשר אותן מאוחר יותר דרך הגדרות הדפדפן.' : error.message === 'identity' ? 'לא הצלחנו לאמת את המכשיר. רעננו את הדף ונסו שוב.' : 'לא הצלחנו להפעיל התראות. נסו שוב.');
    }
  });
  window.addEventListener('plastopil:identity-updated', () => { refresh(); });
  refresh();
});
