document.addEventListener('DOMContentLoaded', () => {
  const button = document.querySelector('#record-button');
  if (!button || !navigator.mediaDevices || !window.MediaRecorder) return;
  const status = document.querySelector('#recording-status');
  const form = document.querySelector('#report-form');
  let recorder;
  let chunks = [];
  let stopTimer;

  button.addEventListener('click', async () => {
    if (recorder?.state === 'recording') { recorder.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true}});
      chunks = [];
      const options = {audioBitsPerSecond: 32000};
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) options.mimeType = 'audio/webm;codecs=opus';
      recorder = new MediaRecorder(stream, options);
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recorder.onstop = () => {
        clearTimeout(stopTimer);
        stream.getTracks().forEach(track => track.stop());
        const type = recorder.mimeType || 'audio/webm';
        const blob = new Blob(chunks, {type});
        const file = new File([blob], `recording-${Date.now()}.webm`, {type});
        const input = document.createElement('input');
        input.type = 'file';
        input.name = 'attachments';
        input.hidden = true;
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
        form.append(input);
        const audio = document.createElement('audio');
        audio.controls = true;
        audio.src = URL.createObjectURL(blob);
        status.textContent = `ההקלטה מוכנה · ${(blob.size / 1024).toFixed(0)}KB`;
        status.append(audio);
        button.innerHTML = '<span class="media-icon">🎙️</span><span>הקלטה קולית<small>הודעה מהמיקרופון</small></span>';
      };
      recorder.start();
      button.textContent = '■ עצור הקלטה';
      status.textContent = 'מקליט בקובץ דחוס · עצירה אוטומטית לאחר 60 שניות…';
      stopTimer = window.setTimeout(() => {
        if (recorder?.state === 'recording') recorder.stop();
      }, 60000);
    } catch {
      status.textContent = 'לא הצלחנו לפתוח את המיקרופון.';
    }
  });
});
