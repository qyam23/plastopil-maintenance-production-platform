document.addEventListener('DOMContentLoaded', () => {
  const button = document.querySelector('#record-button'); if (!button || !navigator.mediaDevices || !window.MediaRecorder) return;
  const status = document.querySelector('#recording-status'), form = document.querySelector('#report-form'); let recorder, chunks = [];
  button.addEventListener('click', async () => {
    if (recorder && recorder.state === 'recording') { recorder.stop(); return; }
    try { const stream = await navigator.mediaDevices.getUserMedia({audio:true}); chunks=[]; recorder = new MediaRecorder(stream);
      recorder.ondataavailable = e => chunks.push(e.data);
      recorder.onstop = () => { stream.getTracks().forEach(t=>t.stop()); const blob=new Blob(chunks,{type:recorder.mimeType}); const file=new File([blob],'recording.webm',{type:blob.type}); const input=document.createElement('input'); input.type='file'; input.name='attachments'; const transfer=new DataTransfer(); transfer.items.add(file); input.files=transfer.files; input.hidden=true; form.append(input); const audio=document.createElement('audio'); audio.controls=true; audio.src=URL.createObjectURL(blob); status.textContent='ההקלטה מוכנה:'; status.append(audio); button.textContent='🎙️ הקלטה'; };
      recorder.start(); button.textContent='■ עצור הקלטה'; status.textContent='מקליט…';
    } catch { status.textContent='לא הצלחנו לפתוח את המיקרופון.'; }
  });
});
