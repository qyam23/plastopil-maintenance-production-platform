document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#report-form');
  if (!form) return;
  const list = document.querySelector('#attachment-list');
  const panel = document.querySelector('#camera-panel');
  const preview = document.querySelector('#camera-preview');
  const status = document.querySelector('#camera-status');
  const videoButton = document.querySelector('#camera-video');
  const identityPanel = document.querySelector('#identity-panel');
  const reporterBar = document.querySelector('#reporter-bar');
  const reporterName = document.querySelector('#reporter-name');
  const deviceLabel = document.querySelector('#device-label');
  let cameraStream, videoRecorder, sending = false;
  let identity = JSON.parse(localStorage.getItem('plastopil_reporter') || 'null');

  let deviceId = identity?.device_id || (crypto.randomUUID ? crypto.randomUUID() : `device-${Date.now()}-${Math.random().toString(16).slice(2)}`);
  document.querySelector('#device-id').value = deviceId;
  const renderIdentity = () => {
    const known = identity?.reporter_name;
    reporterBar.hidden = !known;
    identityPanel.hidden = Boolean(known);
    if (known) {
      document.querySelector('#reporter-display').textContent = `מדווח: ${known}`;
      document.querySelector('#safety-reporter-name').textContent = known;
    }
  };
  const openIdentity = () => { reporterName.value = identity?.reporter_name || ''; deviceLabel.value = identity?.device_label || ''; identityPanel.hidden = false; reporterName.focus(); };
  const saveIdentity = async (name, label) => {
    const send = () => fetch('/api/reporter-devices', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({device_id:deviceId, reporter_name:name, device_label:label})});
    let response = await send();
    if (response.status === 403) {
      deviceId = crypto.randomUUID ? crypto.randomUUID() : `device-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      document.querySelector('#device-id').value = deviceId;
      response = await send();
    }
    if (!response.ok) return false;
    identity = await response.json(); localStorage.setItem('plastopil_reporter', JSON.stringify(identity)); renderIdentity(); window.dispatchEvent(new Event('plastopil:identity-updated')); return true;
  };
  document.querySelector('#change-reporter').addEventListener('click', openIdentity);
  document.querySelector('#safety-change-reporter').addEventListener('click', openIdentity);
  document.querySelector('#save-reporter').addEventListener('click', async () => {
    const name = reporterName.value.trim();
    if (name.length < 2) { reporterName.setCustomValidity('יש להזין שם מלא'); reporterName.reportValidity(); return; }
    if (!await saveIdentity(name, deviceLabel.value.trim())) { alert('לא הצלחנו לשמור את פרטי המדווח. נסו שוב.'); }
  });
  renderIdentity();
  if (identity?.reporter_name) saveIdentity(identity.reporter_name, identity.device_label || '');

  document.querySelectorAll('input[name="report_type"]').forEach(input => input.addEventListener('change', () => {
    document.body.classList.remove('theme-safety', 'theme-maintenance', 'theme-quality');
    const theme = {safety_near_miss:'theme-safety', maintenance_request:'theme-maintenance', process_quality:'theme-quality'}[input.value];
    if (theme) document.body.classList.add(theme);
    document.querySelector('#safety-reporter').hidden = input.value !== 'safety_near_miss' || !identity?.reporter_name;
  }));
  const addFile = (file) => {
    const input = document.createElement('input'); input.type = 'file'; input.name = 'attachments'; input.hidden = true;
    const transfer = new DataTransfer(); transfer.items.add(file); input.files = transfer.files; form.append(input);
    const item = document.createElement('p'); item.textContent = `✓ ${file.name}`; list.appendChild(item);
  };
  document.querySelector('#media-file').addEventListener('change', event => [...event.target.files].forEach(addFile));
  document.querySelector('#files-button').addEventListener('click', () => document.querySelector('#media-file').click());
  const closeCamera = () => { if (cameraStream) cameraStream.getTracks().forEach(track => track.stop()); cameraStream = null; preview.srcObject = null; panel.hidden = true; };
  document.querySelector('#camera-button').addEventListener('click', async () => {
    try { cameraStream = await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}}, audio:false}); preview.srcObject = cameraStream; panel.hidden = false; status.textContent = 'בחרו תמונה או וידאו.'; }
    catch { status.textContent = 'לא הצלחנו לפתוח את המצלמה. אפשר לצרף קבצים במקום.'; panel.hidden = false; }
  });
  document.querySelector('#camera-stop').addEventListener('click', closeCamera);
  document.querySelector('#camera-photo').addEventListener('click', () => {
    if (!cameraStream) return;
    const canvas = document.createElement('canvas'); canvas.width = preview.videoWidth; canvas.height = preview.videoHeight; canvas.getContext('2d').drawImage(preview, 0, 0);
    canvas.toBlob(blob => { addFile(new File([blob], `photo-${Date.now()}.jpg`, {type:'image/jpeg'})); closeCamera(); }, 'image/jpeg', .9);
  });
  videoButton.addEventListener('click', () => {
    if (!cameraStream || !window.MediaRecorder) { status.textContent = 'הדפדפן אינו תומך בהקלטת וידאו.'; return; }
    if (!videoRecorder || videoRecorder.state === 'inactive') {
      const chunks = []; videoRecorder = new MediaRecorder(cameraStream); videoRecorder.ondataavailable = event => chunks.push(event.data);
      videoRecorder.onstop = () => { addFile(new File([new Blob(chunks,{type:videoRecorder.mimeType})], `video-${Date.now()}.webm`, {type:videoRecorder.mimeType})); closeCamera(); };
      videoRecorder.start(); videoButton.textContent = 'עצור וידאו'; status.textContent = 'מקליט וידאו…';
    } else { videoRecorder.stop(); videoButton.textContent = 'התחל וידאו'; }
  });
  form.addEventListener('submit', async event => {
    if (sending) return;
    if (!identity?.reporter_name) { event.preventDefault(); openIdentity(); return; }
    event.preventDefault(); const button = form.querySelector('.send'); button.disabled = true; button.textContent = 'שולח דיווח…';
    if (!await saveIdentity(identity.reporter_name, identity.device_label || '')) { button.disabled = false; button.textContent = 'שלח דיווח'; alert('לא הצלחנו לאמת את המדווח. נסו שוב.'); return; }
    sending = true; form.submit();
  });
});
