(() => {
  document.querySelectorAll('form').forEach((form) => {
    const button = form.querySelector('.send-progress-button[type="submit"]');
    if (!button) return;

    form.addEventListener('submit', (event) => {
      if (button.dataset.sending === 'true') {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      button.dataset.sending = 'true';
      button.classList.add('is-sending');
      button.disabled = true;
      const label = button.querySelector('.button-label');
      if (label) label.textContent = 'שולחים…';
      window.setTimeout(() => form.submit(), 760);
    });
  });
})();
