(function () {
  function showInsertedBootstrapModals(root) {
    if (!window.bootstrap) {
      console.error("Bootstrap JS is not loaded.");
      return;
    }

    const modals = root.matches?.("[data-auto-show-modal]")
      ? [root]
      : root.querySelectorAll("[data-auto-show-modal]");

    modals.forEach((modalEl) => {
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.show();

      modalEl.addEventListener(
        "hidden.bs.modal",
        () => {
          modal.dispose();
          modalEl.remove();

          const modalRoot = document.getElementById("modal-root");
          if (modalRoot && !modalRoot.querySelector(".modal")) {
            modalRoot.innerHTML = "";
          }
        },
        { once: true }
      );
    });
  }

  function closeOpenModals() {
    if (!window.bootstrap) return;

    document.querySelectorAll(".modal.show").forEach((modalEl) => {
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.hide();
    });

    // Fallback cleanup if the modal was already replaced/removed oddly.
    setTimeout(() => {
      document.body.classList.remove("modal-open");
      document.querySelectorAll(".modal-backdrop").forEach((el) => el.remove());
    }, 300);
  }

  document.body.addEventListener("htmx:afterSwap", (event) => {
    showInsertedBootstrapModals(event.detail.target);
  });

  document.body.addEventListener("modal-close", () => {
    closeOpenModals();
  });
})();

(function () {
  const messageBuffer = [];

  function ensureToastRegion() {
    let region = document.getElementById("toast-region");

    if (!region) {
      region = document.createElement("div");
      region.id = "toast-region";
      region.className = "toast-region";
      region.setAttribute("aria-live", "polite");
      document.body.appendChild(region);
    }

    return region;
  }

  function pushMessage(payload) {
    const message =
      typeof payload === "string"
        ? payload
        : payload?.message || "Done.";

    const level =
      typeof payload === "string"
        ? "info"
        : payload?.level || "info";

    const item = {
      message,
      level,
      time: new Date(),
    };

    messageBuffer.unshift(item);
    window.kooplexMessages = messageBuffer;

    showToast(item);
    updateMessageBadge();
  }

  function showToast(item) {
    const region = ensureToastRegion();

    const toast = document.createElement("div");
    toast.className = `kooplex-toast kooplex-toast-${item.level}`;
    toast.textContent = item.message;

    region.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("is-hiding");
    }, 3500);

    setTimeout(() => {
      toast.remove();
    }, 4200);
  }

  function updateMessageBadge() {
    const badge = document.querySelector("[data-message-count]");
    if (!badge) return;

    badge.textContent = String(messageBuffer.length);
    badge.hidden = messageBuffer.length === 0;
  }

  function renderMessagePanel() {
    const panel = document.getElementById("side-panel");
    if (!panel) return;

    const items = messageBuffer
      .map((item) => {
        return `
          <li class="message-item">
            <div class="message-text">${escapeHtml(item.message)}</div>
            <div class="message-time">${item.time.toLocaleTimeString()}</div>
          </li>
        `;
      })
      .join("");

    panel.innerHTML = `
      <aside class="slide-panel">
        <header class="slide-panel-header">
          <h2>Messages</h2>
          <button type="button" class="icon-button" data-close-panel>×</button>
        </header>
        <div class="slide-panel-body">
          ${
            items
              ? `<ul class="message-list">${items}</ul>`
              : `<p class="text-muted">No messages yet.</p>`
          }
        </div>
      </aside>
    `;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  document.body.addEventListener("kooplex-toast", (event) => {
    pushMessage(event.detail);
  });

  document.body.addEventListener("click", (event) => {
    if (event.target.closest("[data-open-messages]")) {
      renderMessagePanel();
    }

    if (event.target.closest("[data-close-panel]")) {
      const panel = document.getElementById("side-panel");
      if (panel) panel.innerHTML = "";
    }
  });
})();
