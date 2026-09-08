document.addEventListener('DOMContentLoaded', () => {
  const live = document.querySelector('#report-live');
  if (!live?.dataset.updatesUrl) return;

  let updatedAt = live.dataset.updatedAt;
  const checkForUpdates = async () => {
    if (document.hidden) return;
    try {
      const response = await fetch(live.dataset.updatesUrl, { cache: 'no-store' });
      if (!response.ok) return;
      const update = await response.json();
      if (update.updated_at && updatedAt && update.updated_at !== updatedAt) window.location.reload();
      updatedAt = update.updated_at || updatedAt;
    } catch { /* A temporary network loss must not disturb an active report form. */ }
  };

  setInterval(checkForUpdates, 15000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) checkForUpdates(); });
});
