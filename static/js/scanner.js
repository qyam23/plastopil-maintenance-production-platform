window.addEventListener('load', () => {
  const message = document.querySelector('#scanner-message');
  const manualInput = document.querySelector('#manual-location');
  const manualSubmit = document.querySelector('#manual-location-submit');
  const cameraSelect = document.querySelector('#camera-select');
  const startButton = document.querySelector('#start-scanner');
  let scanner;
  let redirected = false;

  const openReport = (locationCode) => {
    const code = String(locationCode || '').trim();
    if (!code || redirected) return;
    redirected = true;
    message.textContent = 'הקוד זוהה. פותחים דיווח…';
    // Do not wait for stop(): Android can keep it pending while the browser
    // displays or closes a camera-permission prompt.
    if (scanner) { try { scanner.stop().catch(() => {}); } catch (_) {} }
    window.setTimeout(() => window.location.assign(`/report/new?location=${encodeURIComponent(code)}`), 80);
  };

  const locationFromQr = (decodedText) => {
    const raw = String(decodedText || '').trim();
    try {
      const location = new URL(raw).searchParams.get('location');
      if (location) return location;
    } catch (_) { /* Older QR codes may contain only a location code. */ }
    return raw;
  };

  const cameraError = (error) => {
    const reason = error?.name === 'NotAllowedError' ? 'גישה למצלמה נחסמה.'
      : error?.name === 'NotReadableError' ? 'המצלמה נמצאת בשימוש באפליקציה אחרת.'
      : 'לא הצלחנו להפעיל את המצלמה.';
    message.textContent = `${reason} סגרו אפליקציית מצלמה אחרת, אשרו הרשאה ולחצו שוב על “הפעל מצלמה לסריקה”.`;
    startButton.disabled = false;
    startButton.textContent = 'נסה להפעיל מצלמה שוב';
  };

  const populateCameras = async () => {
    const cameras = await Html5Qrcode.getCameras();
    if (!cameras.length) throw new Error('No camera available');
    cameraSelect.replaceChildren(...cameras.map((camera, index) => {
      const option = document.createElement('option');
      option.value = camera.id;
      option.textContent = camera.label || `מצלמה ${index + 1}`;
      return option;
    }));
    const preferred = cameras.findIndex(camera => /back|rear|environment|main/i.test(camera.label));
    cameraSelect.selectedIndex = preferred >= 0 ? preferred : 0;
    cameraSelect.hidden = cameras.length < 2;
  };

  const startScanner = async () => {
    if (!window.Html5Qrcode) { cameraError(); return; }
    startButton.disabled = true;
    startButton.textContent = 'מפעיל מצלמה…';
    message.textContent = 'אשרו את גישת המצלמה בדפדפן.';
    try {
      await populateCameras();
      scanner = new Html5Qrcode('qr-reader');
      await scanner.start(cameraSelect.value, { fps: 10, qrbox: { width: 240, height: 240 }, aspectRatio: 1 },
        decodedText => openReport(locationFromQr(decodedText)), () => {});
      message.textContent = 'כוונו את המצלמה אל קוד ה־QR.';
      startButton.hidden = true;
    } catch (error) { cameraError(error); }
  };

  startButton.addEventListener('click', startScanner);
  manualSubmit.addEventListener('click', () => {
    const value = manualInput.value.trim();
    if (!value) { manualInput.focus(); return; }
    openReport(locationFromQr(value));
  });
  manualInput.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); manualSubmit.click(); }
  });
});
