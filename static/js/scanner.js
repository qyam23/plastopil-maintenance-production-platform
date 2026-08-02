window.addEventListener('load', () => {
  const message = document.querySelector('#scanner-message');
  const qr = new Html5Qrcode('qr-reader');
  qr.start({facingMode: 'environment'}, {fps: 10, qrbox: {width: 240, height: 240}}, code => {
    qr.stop().finally(() => { window.location.href = `/report/new?location=${encodeURIComponent(code)}`; });
  }).catch(() => { message.textContent = 'לא הצלחנו לפתוח את המצלמה. אפשר לנסות שוב או לעבור לדיווח ישיר.'; });
});
