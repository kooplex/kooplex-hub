(function () {
  const MODAL_ROOT_ID = "modal-root";

  function showInsertedBootstrapModal(modalRoot) {
    if (!window.bootstrap) {
      console.error("Bootstrap JS is not loaded.");
      return;
    }

    const modalEl = modalRoot.querySelector("[data-auto-show-modal]");

    if (!modalEl) {
      return;
    }

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

    // Do not show an already-open modal again.
    if (!modalEl.classList.contains("show")) {
      modal.show();
    }

    modalEl.addEventListener(
      "hidden.bs.modal",
      () => {
        modal.dispose();
        modalRoot.innerHTML = "";
      },
      { once: true }
    );
  }

  function closeOpenModals() {
    if (!window.bootstrap) {
      return;
    }

    document.querySelectorAll(".modal.show").forEach((modalEl) => {
      bootstrap.Modal.getOrCreateInstance(modalEl).hide();
    });

    // Defensive recovery from stale Bootstrap state.
    setTimeout(() => {
      if (!document.querySelector(".modal.show")) {
        document.body.classList.remove("modal-open");
        document.body.style.removeProperty("overflow");
        document.body.style.removeProperty("padding-right");

        document
          .querySelectorAll(".modal-backdrop")
          .forEach((backdrop) => backdrop.remove());
      }
    }, 350);
  }

  document.body.addEventListener("htmx:afterSwap", (event) => {
    const target = event.detail.target;

    if (target.id !== MODAL_ROOT_ID) {
      return;
    }

    showInsertedBootstrapModal(target);
  });

  document.body.addEventListener("modal-close", closeOpenModals);
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






document.body.addEventListener("htmx:afterSwap", (event) => {
  const target = event.detail.target;

  if (!target.matches?.(".membership-member-list")) {
    return;
  }

  // Remove the empty-state placeholder after the first member is added.
  target
    .querySelectorAll("[data-membership-empty]")
    .forEach((element) => element.remove());

  const rows = target.querySelectorAll("[data-membership-member]");
  const newestRow = rows[rows.length - 1];

  if (!newestRow) {
    return;
  }

  newestRow.scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });

  newestRow.classList.add("membership-member-row-added");

  window.setTimeout(() => {
    newestRow.classList.remove("membership-member-row-added");
  }, 1200);
});

document.body.addEventListener("htmx:afterRequest", (event) => {
  const trigger = event.detail.elt;

  if (
    !event.detail.successful ||
    !trigger.matches?.("[data-membership-search-result]")
  ) {
    return;
  }

  const listGroup = trigger.closest(".list-group");
  trigger.remove();
  if (listGroup && !listGroup.children.length) {
    listGroup.outerHTML = `
      <div class="text-muted small p-2">
        No additional matching users.
      </div>
    `;
  }
});

document.addEventListener("click", (event) => {
  const removeButton = event.target.closest("[data-membership-remove]");

  if (!removeButton) {
    return;
  }

  const memberRow = removeButton.closest("[data-membership-member]");

  if (!memberRow) {
    return;
  }

  const memberList = memberRow.closest(".membership-member-list");

  memberRow.remove();

  if (
    memberList &&
    !memberList.querySelector("[data-membership-member]")
  ) {
    const emptyState = document.createElement("div");

    emptyState.className =
      "membership-empty text-muted small text-center py-4";

    emptyState.dataset.membershipEmpty = "";
    emptyState.textContent = "No additional members selected.";

    memberList.appendChild(emptyState);
  }
});

document.body.addEventListener("closeModal", (event) => {
    const modalId = event.detail?.modalId;

    if (!modalId || typeof bootstrap === "undefined") {
        return;
    }

    const element = document.getElementById(modalId);

    if (!element) {
        return;
    }

    const modal = bootstrap.Modal.getInstance(element);

    if (modal) {
        modal.hide();
    }

    element.addEventListener(
        "hidden.bs.modal",
        () => {
            const modalRoot = document.getElementById("modal-root");

            if (modalRoot) {
                modalRoot.innerHTML = "";
            }
        },
        { once: true }
    );
});


document.body.addEventListener(
  "htmx:beforeSwap",
  (event) => {
    if (
      event.detail.xhr.status === 422
    ) {
      event.detail.shouldSwap = true;
      event.detail.isError = false;
    }
  },
);
