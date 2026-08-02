window.addEventListener('load', () => {
  const message = document.querySelector('#scanner-message');
  const manualInput = document.querySelector('#manual-location');
  const manualSubmit = document.querySelector('#manual-location-submit');
  let scanner;
  let redirected = false;

  const openReport = (locationCode) => {
    const code = String(locationCode || '').trim();
    if (!code || redirected) return;
    redirected = true;
    message.textContent = 'הקוד זוהה. פותחים דיווח…';
    if (scanner) scanner.stop().catch(() => {}).finally(() => {
      window.location.assign(`/report/new?location=${encodeURIComponent(code)}`);
    });
    else window.location.assign(`/report/new?location=${encodeURIComponent(code)}`);
  };

  // Manager QR codes contain the full report URL. Extract its location first.
  const locationFromQr = (decodedText) => {
    const raw = String(decodedText || '').trim();
    try {
      const url = new URL(raw);
      const location = url.searchParams.get('location');
      if (location) return location;
    } catch (_) { /* Legacy QR codes can contain only a location code. */ }
    return raw;
  };

  const showCameraError = () => {
    message.textContent = 'לא הצלחנו לפתוח את המצלמה. אשרו הרשאת מצלמה בדפדפן, או הזינו את קוד המיקום ידנית.';
  };
  const onScan = (decodedText) => openReport(locationFromQr(decodedText));
  const config = { fps: 10, qrbox: { width: 240, height: 240 }, aspectRatio: 1 };

  const start = async () => {
    if (!window.Html5Qrcode) { showCameraError(); return; }
    scanner = new Html5Qrcode('qr-reader');
    message.textContent = 'מפעילים מצלמה אחורית…';
    try {
      await scanner.start({ facingMode: { ideal: 'environment' } }, config, onScan, () => {});
      message.textContent = 'כוונו את המצלמה אל קוד ה־QR.';
    } catch (_) {
      try {
        const cameras = await Html5Qrcode.getCameras();
        const preferred = cameras.find(camera => /back|rear|environment/i.test(camera.label)) || cameras[0];
        if (!preferred) throw new Error('No camera available');
        await scanner.start(preferred.id, config, onScan, () => {});
        message.textContent = 'כוונו את המצלמה אל קוד ה־QR.';
      } catch (_) { showCameraError(); }
    }
  };

  manualSubmit.addEventListener('click', () => {
    const value = manualInput.value.trim();
    if (!value) { manualInput.focus(); return; }
    openReport(locationFromQr(value));
  });
  manualInput.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); manualSubmit.click(); }
  });
  start();
});
