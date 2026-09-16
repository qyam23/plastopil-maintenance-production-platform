document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#report-form');
  if (!form) return;

  const list = document.querySelector('#attachment-list');
  const panel = document.querySelector('#camera-panel');
  const preview = document.querySelector('#camera-preview');
  const cameraStatus = document.querySelector('#camera-status');
  const videoButton = document.querySelector('#camera-video');
  const identityPanel = document.querySelector('#identity-panel');
  const reporterBar = document.querySelector('#reporter-bar');
  const reporterName = document.querySelector('#reporter-name');
  const deviceLabel = document.querySelector('#device-label');
  const contactDetail = document.querySelector('#contact-detail');
  const pushPanel = document.querySelector('#push-panel');
  const contactStatus = document.querySelector('#contact-status');
  const submitButton = form.querySelector('.upload-progress-button');
  const submitLabel = submitButton.querySelector('.send-label');
  const progressFill = submitButton.querySelector('.upload-progress-fill');
  const progressPercent = submitButton.querySelector('.upload-progress-percent');
  const progressStatus = document.querySelector('#upload-progress-status');
  let cameraStream;
  let videoRecorder;
  let videoTimer;
  let sending = false;

  const readIdentity = () => {
    try { return JSON.parse(localStorage.getItem('plastopil_reporter') || 'null'); }
    catch { return null; }
  };
  let identity = readIdentity();
  let deviceId = identity?.device_id || (crypto.randomUUID ? crypto.randomUUID() : `device-${Date.now()}-${Math.random().toString(16).slice(2)}`);
  document.querySelector('#device-id').value = deviceId;

  const updateCommunicationState = () => {
    const pushActive = window.plastopilPushActive === true;
    const hasContact = Boolean(identity?.contact_detail?.trim());
    pushPanel.classList.toggle('contact-ready', pushActive || hasContact);
    pushPanel.classList.toggle('needs-contact', !pushActive && !hasContact);
    contactStatus.textContent = pushActive
      ? '✓ עדכונים יישלחו בהתראת דפדפן.'
      : hasContact
        ? `✓ נשמרה חלופת קשר: ${identity.contact_detail}`
        : 'לפני השליחה יש לאפשר התראות או להזין מספר נייד / כינוי קשר.';
  };

  const renderIdentity = () => {
    const known = identity?.reporter_name;
    reporterBar.hidden = !known;
    identityPanel.hidden = Boolean(known);
    if (known) {
      document.querySelector('#reporter-display').textContent = `מדווח: ${known}`;
      document.querySelector('#safety-reporter-name').textContent = known;
    }
    updateCommunicationState();
  };

  const openIdentity = () => {
    reporterName.value = identity?.reporter_name || '';
    deviceLabel.value = identity?.device_label || '';
    contactDetail.value = identity?.contact_detail || '';
    identityPanel.hidden = false;
    reporterName.focus();
  };

  const saveIdentity = async (name, label, contact) => {
    const send = () => fetch('/api/reporter-devices', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({device_id: deviceId, reporter_name: name, device_label: label, contact_detail: contact}),
    });
    let response = await send();
    if (response.status === 403) {
      deviceId = crypto.randomUUID ? crypto.randomUUID() : `device-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      document.querySelector('#device-id').value = deviceId;
      response = await send();
    }
    if (!response.ok) return false;
    identity = await response.json();
    localStorage.setItem('plastopil_reporter', JSON.stringify(identity));
    renderIdentity();
    window.dispatchEvent(new Event('plastopil:identity-updated'));
    return true;
  };

  window.plastopilEnsureReporter = async () => {
    const current = readIdentity();
    if (!current?.reporter_name) return false;
    return saveIdentity(current.reporter_name, current.device_label || '', current.contact_detail || '');
  };

  document.querySelector('#change-reporter').addEventListener('click', openIdentity);
  document.querySelector('#safety-change-reporter').addEventListener('click', openIdentity);
  document.querySelector('#save-reporter').addEventListener('click', async () => {
    const name = reporterName.value.trim();
    reporterName.setCustomValidity(name.length < 2 ? 'יש להזין שם מלא' : '');
    if (!reporterName.reportValidity()) return;
    if (!await saveIdentity(name, deviceLabel.value.trim(), contactDetail.value.trim())) {
      alert('לא הצלחנו לשמור את פרטי המדווח. נסו שוב.');
    }
  });

  renderIdentity();
  window.plastopilReporterReady = identity?.reporter_name ? window.plastopilEnsureReporter() : Promise.resolve(false);
  window.addEventListener('plastopil:push-status', event => {
    window.plastopilPushActive = Boolean(event.detail?.active);
    updateCommunicationState();
  });

  document.querySelectorAll('input[name="report_type"]:not(:disabled)').forEach(input => input.addEventListener('change', () => {
    document.body.classList.remove('theme-safety', 'theme-maintenance', 'theme-quality');
    const theme = {safety_near_miss: 'theme-safety', maintenance_request: 'theme-maintenance'}[input.value];
    if (theme) document.body.classList.add(theme);
    document.querySelector('#safety-reporter').hidden = input.value !== 'safety_near_miss' || !identity?.reporter_name;
  }));

  const compressImage = async file => {
    if (!file.type.startsWith('image/') || file.type === 'image/gif' || !window.createImageBitmap) return file;
    try {
      const bitmap = await createImageBitmap(file);
      const scale = Math.min(1, 1920 / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      canvas.getContext('2d', {alpha: false}).drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close();
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .82));
      if (!blob || blob.size >= file.size) return file;
      return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', {type: 'image/jpeg', lastModified: Date.now()});
    } catch { return file; }
  };

  const addFile = async originalFile => {
    const pending = document.createElement('p');
    pending.textContent = originalFile.type.startsWith('image/') ? `מקטינים את ${originalFile.name}…` : `מכינים את ${originalFile.name}…`;
    list.appendChild(pending);
    const file = await compressImage(originalFile);
    const input = document.createElement('input');
    input.type = 'file';
    input.name = 'attachments';
    input.hidden = true;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    form.append(input);
    const saved = Math.max(0, originalFile.size - file.size);
    pending.textContent = `✓ ${file.name} · ${(file.size / 1024 / 1024).toFixed(1)}MB${saved > 1024 ? ` · נחסכו ${(saved / 1024 / 1024).toFixed(1)}MB` : ''}`;
  };

  document.querySelector('#media-file').addEventListener('change', async event => {
    for (const file of [...event.target.files]) await addFile(file);
    event.target.value = '';
  });
  document.querySelector('#files-button').addEventListener('click', () => document.querySelector('#media-file').click());

  const closeCamera = () => {
    clearTimeout(videoTimer);
    if (cameraStream) cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
    preview.srcObject = null;
    panel.hidden = true;
  };

  document.querySelector('#camera-button').addEventListener('click', async () => {
    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({
        video: {facingMode: {ideal: 'environment'}, width: {ideal: 1280}, height: {ideal: 720}},
        audio: false,
      });
      preview.srcObject = cameraStream;
      panel.hidden = false;
      cameraStatus.textContent = 'צילום מותאם ל־720p כדי לחסוך נפח.';
    } catch {
      cameraStatus.textContent = 'לא הצלחנו לפתוח את המצלמה. אפשר לצרף קבצים במקום.';
      panel.hidden = false;
    }
  });
  document.querySelector('#camera-stop').addEventListener('click', closeCamera);
  document.querySelector('#camera-photo').addEventListener('click', () => {
    if (!cameraStream) return;
    const scale = Math.min(1, 1920 / Math.max(preview.videoWidth, preview.videoHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(preview.videoWidth * scale);
    canvas.height = Math.round(preview.videoHeight * scale);
    canvas.getContext('2d', {alpha: false}).drawImage(preview, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async blob => {
      await addFile(new File([blob], `photo-${Date.now()}.jpg`, {type: 'image/jpeg'}));
      closeCamera();
    }, 'image/jpeg', .82);
  });

  videoButton.addEventListener('click', () => {
    if (!cameraStream || !window.MediaRecorder) {
      cameraStatus.textContent = 'הדפדפן אינו תומך בהקלטת וידאו.';
      return;
    }
    if (!videoRecorder || videoRecorder.state === 'inactive') {
      const chunks = [];
      const options = {videoBitsPerSecond: 1200000};
      if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) options.mimeType = 'video/webm;codecs=vp8';
      videoRecorder = new MediaRecorder(cameraStream, options);
      videoRecorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      videoRecorder.onstop = async () => {
        clearTimeout(videoTimer);
        const type = videoRecorder.mimeType || 'video/webm';
        await addFile(new File([new Blob(chunks, {type})], `video-${Date.now()}.webm`, {type}));
        videoButton.textContent = 'התחל וידאו';
        closeCamera();
      };
      videoRecorder.start();
      videoButton.textContent = 'עצור וידאו';
      cameraStatus.textContent = 'מקליט וידאו 720p · עצירה אוטומטית לאחר 60 שניות.';
      videoTimer = window.setTimeout(() => {
        if (videoRecorder?.state === 'recording') videoRecorder.stop();
      }, 60000);
    } else {
      videoRecorder.stop();
    }
  });

  const setProgress = (percent, text) => {
    const value = Math.max(0, Math.min(100, Math.round(percent)));
    progressFill.style.width = `${value}%`;
    progressPercent.textContent = `${value}%`;
    progressStatus.textContent = text;
  };

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (sending || !form.reportValidity()) return;
    if (!identity?.reporter_name) { openIdentity(); return; }
    const pushActive = window.plastopilPushActive === true;
    if (!pushActive && !identity.contact_detail?.trim()) {
      openIdentity();
      contactDetail.setCustomValidity('יש להזין מספר נייד או כינוי קשר, או לאפשר התראות');
      contactDetail.reportValidity();
      contactDetail.addEventListener('input', () => contactDetail.setCustomValidity(''), {once: true});
      return;
    }

    submitButton.disabled = true;
    submitButton.classList.add('is-uploading');
    submitLabel.textContent = 'שולחים דיווח';
    setProgress(2, 'מאמתים את פרטי המדווח…');
    if (!await saveIdentity(identity.reporter_name, identity.device_label || '', identity.contact_detail || '')) {
      submitButton.disabled = false;
      submitButton.classList.remove('is-uploading');
      submitLabel.textContent = 'שלח דיווח';
      setProgress(0, 'לא הצלחנו לאמת את המדווח. נסו שוב.');
      return;
    }

    sending = true;
    const xhr = new XMLHttpRequest();
    xhr.open('POST', form.action || window.location.href);
    xhr.upload.addEventListener('progress', uploadEvent => {
      if (uploadEvent.lengthComputable) {
        const percent = Math.max(3, Math.min(95, uploadEvent.loaded / uploadEvent.total * 95));
        setProgress(percent, `מעלים את הדיווח והקבצים… ${Math.round(percent)}%`);
      } else {
        setProgress(35, 'מעלים את הדיווח והקבצים…');
      }
    });
    xhr.upload.addEventListener('load', () => setProgress(96, 'הקבצים הועלו. שומרים את הדיווח…'));
    xhr.addEventListener('load', () => {
      const destination = xhr.responseURL || '';
      let successPath = false;
      try { successPath = new URL(destination).pathname.startsWith('/report/success/'); } catch { successPath = false; }
      if (xhr.status >= 200 && xhr.status < 400 && successPath) {
        setProgress(100, '✓ הדיווח נשלח בהצלחה');
        progressStatus.classList.add('success');
        submitButton.classList.add('is-complete');
        submitLabel.textContent = 'הדיווח נשלח';
        window.setTimeout(() => { window.location.assign(destination); }, 650);
      } else if (xhr.status >= 200 && xhr.status < 400 && destination) {
        window.location.assign(destination);
      } else {
        sending = false;
        submitButton.disabled = false;
        submitButton.classList.remove('is-uploading');
        submitLabel.textContent = 'שלח דיווח';
        setProgress(0, 'השליחה נכשלה. בדקו את החיבור ונסו שוב.');
      }
    });
    xhr.addEventListener('error', () => {
      sending = false;
      submitButton.disabled = false;
      submitButton.classList.remove('is-uploading');
      submitLabel.textContent = 'שלח דיווח';
      setProgress(0, 'אין חיבור לשרת. הדיווח לא נשלח.');
    });
    xhr.send(new FormData(form));
  });
});
