document.addEventListener('DOMContentLoaded', () => {
  const casePage = document.querySelector('.digital-case');
  if (!casePage) return;
  const state = document.querySelector('#receipt-state');
  const button = document.querySelector('#case-ack');
  let viewed = state.textContent.includes('נצפה') || state.textContent.includes('אושר');
  const send = async (action) => {
    const body = new FormData(); body.append('action', action);
    const response = await fetch(casePage.dataset.receiptUrl, {method: 'POST', body, credentials: 'same-origin'});
    if (!response.ok) throw new Error('לא ניתן לשמור אישור כרגע');
    return response.json();
  };
  let viewTimer;
  const scheduleView = () => {
    clearTimeout(viewTimer);
    if (viewed || document.visibilityState !== 'visible') return;
    viewTimer = window.setTimeout(async () => {
      if (document.visibilityState !== 'visible') return;
      try { const data = await send('view'); viewed = true; state.textContent = `התיק נצפה: ${data.viewed_at} · ממתין לאישור טיפול`; }
      catch { state.textContent = 'לא ניתן לשמור אישור צפייה כרגע'; }
    }, 3000);
  };
  document.addEventListener('visibilitychange', scheduleView);
  scheduleView();
  button?.addEventListener('click', async () => {
    button.disabled = true;
    try { const data = await send('acknowledge'); state.textContent = `אושר לטיפול: ${data.acknowledged_at}`; button.textContent = 'הקבלה אושרה ✓'; }
    catch { button.disabled = false; state.textContent = 'האישור לא נשמר. נסו שוב.'; }
  });
});
