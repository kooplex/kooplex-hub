document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-project-card]").forEach((card) => {
    const projectId = card.dataset.projectCard;
    const storageKey = `project-active-tab:${projectId}`;

    const savedTabId = localStorage.getItem(storageKey);

    if (savedTabId) {
      const savedTab = card.querySelector(
        `#${CSS.escape(savedTabId)}`
      );

      if (savedTab && window.bootstrap) {
        bootstrap.Tab.getOrCreateInstance(savedTab).show();
      }
    }

    card.addEventListener("shown.bs.tab", (event) => {
      const tab = event.target;

      if (tab.matches("[data-project-tab]")) {
        localStorage.setItem(storageKey, tab.id);
      }
    });
  });
});
