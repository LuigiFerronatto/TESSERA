document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
  const code = document.getElementById(button.dataset.copy);
  const status = button.nextElementSibling;
  try {
    await navigator.clipboard.writeText(code.textContent);
    status.textContent = 'Copied.';
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(code);
    selection.removeAllRanges();
    selection.addRange(range);
    status.textContent = 'Select and copy the highlighted text.';
  }
}));
