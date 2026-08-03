document.body.addEventListener("change", event => {
  if (!event.target.matches("[data-mounts-choice]")) {
    return;
  }

  const form = event.target.closest("[data-mounts-form]");

  if (!form) {
    return;
  }

  const saveButton = form.querySelector(
    "[data-mounts-save]"
  );

  if (saveButton) {
    saveButton.disabled = false;
  }
});
