(function () {
  const STORAGE_PREFIX = "kooplex-course-tab:";

  function storageKey(card) {
    return STORAGE_PREFIX + card.dataset.id;
  }

  function restoreCard(card) {
    const target = localStorage.getItem(storageKey(card));
    if (!target) {
      return;
    }

    const button = [ ...card.querySelectorAll('[data-bs-toggle="tab"]') ]
      .find((candidate) => candidate.dataset.bsTarget === target);

    if (!button) {
      return;
    }

    bootstrap.Tab.getOrCreateInstance(button).show();
  }

  document.addEventListener("shown.bs.tab", (event) => {
    const button = event.target;

    const card = button.closest('[data-widget="coursecard"]');
    if (!card) {
      return;
    }

    const target = button.dataset.bsTarget;
    if (target) {
      localStorage.setItem(storageKey(card), target);
    }
  });

  function restoreAll(root = document) {
    root
      .querySelectorAll('[data-widget="coursecard"]')
      .forEach(restoreCard);
  }

  document.addEventListener("DOMContentLoaded", () => {
    restoreAll();
  });

  document.body.addEventListener("htmx:afterSwap", (event) => {
    restoreAll(event.target);
  });
})();
