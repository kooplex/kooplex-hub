document.body.addEventListener("click", event => {
    const removeButton = event.target.closest(
        "[data-membership-remove]"
    );

    if (!removeButton) {
        return;
    }

    const row = removeButton.closest(
        "[data-membership-row]"
    );

    const form = removeButton.closest(
        "[data-membership-form]"
    );

    row?.remove();

    const saveButton = form?.querySelector(
        "[data-membership-save]"
    );

    if (saveButton) {
        saveButton.disabled = false;
    }
});

document.body.addEventListener("change", event => {
    if (!event.target.matches("[data-membership-role]")) {
        return;
    }

    const form = event.target.closest(
        "[data-membership-form]"
    );

    const saveButton = form?.querySelector(
        "[data-membership-save]"
    );

    if (saveButton) {
        saveButton.disabled = false;
    }
});

document.body.addEventListener("htmx:afterSwap", (event) => {
  const target = event.detail.target;

  if (!target.matches("[data-membership-selected-members]")) {
    return;
  }

  const form = target.closest("[data-membership-form]");

  if (!form) {
    return;
  }

  const saveButton = form.querySelector(
    "[data-membership-save]"
  );

  if (saveButton) {
    saveButton.disabled = false;
  }
});

document.body.addEventListener("htmx:beforeSwap", (event) => {
  const target = event.detail.target;

  if (!target.matches("[data-membership-selected-members]")) {
    return;
  }

  target
    .querySelector("[data-membership-empty]")
    ?.remove();
});


function initializeMembershipForm(form) {
    const saveButton = form.querySelector(
        "[data-membership-save]"
    );

    if (!saveButton) {
        return;
    }

    const markDirty = () => {
        saveButton.disabled = false;
        form.dataset.dirty = "true";
    };

    form.addEventListener("change", event => {
        if (
            event.target.matches(
                "[name^='member_role_']"
            )
        ) {
            markDirty();
        }
    });

    form.addEventListener(
        "membership:member-added",
        markDirty
    );

    form.addEventListener(
        "membership:member-removed",
        markDirty
    );
}

document.body.addEventListener(
    "htmx:afterSwap",
    event => {
        event.target
            .querySelectorAll("[data-membership-form]")
            .forEach(initializeMembershipForm);
    }
);

document.body.addEventListener(
    "click",
    event => {
        const removeButton = event.target.closest(
            "[data-member-remove]"
        );

        if (!removeButton) {
            return;
        }

        const row = removeButton.closest(
            "[data-member-row]"
        );

        const form = removeButton.closest(
            "[data-membership-form]"
        );

        row?.remove();

        form?.dispatchEvent(
            new CustomEvent(
                "membership:member-removed"
            )
        );
    }
);

document.body.addEventListener(
    "closeModal",
    event => {
        const modalId = event.detail.modalId;
        const modalElement = document.getElementById(
            modalId
        );

        if (!modalElement) {
            console.warn(
                "Modal not found:",
                modalId
            );
            return;
        }

        const modal = bootstrap.Modal.getOrCreateInstance(
            modalElement
        );

        modal.hide();
    }
);









/*
















function markMembershipDirty(editor) {
    const saveButton = editor.querySelector(
        "[data-membership-save]"
    );

    if (saveButton) {
        saveButton.disabled = false;
    }
}

function updateMembershipEmptyState(editor) {
    const list = editor.querySelector(
        "[data-membership-list]"
    );

    if (!list) {
        return;
    }

    const rows = list.querySelectorAll(
        "[data-membership-row]"
    );

    const empty = list.querySelector(
        "[data-membership-empty]"
    );

    if (rows.length > 0) {
        empty?.remove();
        return;
    }

    if (!empty) {
        const message = document.createElement("p");
        message.className = "text-muted";
        message.dataset.membershipEmpty = "";
        message.textContent = "No members selected.";
        list.appendChild(message);
    }
}

document.addEventListener("click", function (event) {
    const removeButton = event.target.closest(
        "[data-membership-remove]"
    );

    if (!removeButton) {
        return;
    }

    const editor = removeButton.closest(
        "[data-membership-editor]"
    );

    const row = removeButton.closest(
        "[data-membership-row]"
    );

    if (!editor || !row) {
        return;
    }

    row.remove();

    updateMembershipEmptyState(editor);
    markMembershipDirty(editor);
});

document.addEventListener("change", function (event) {
    if (!event.target.matches("[data-membership-role]")) {
        return;
    }

    const editor = event.target.closest(
        "[data-membership-editor]"
    );

    if (editor) {
        markMembershipDirty(editor);
    }
});

document.body.addEventListener(
    "htmx:afterSwap",
    function (event) {
        const target = event.detail.target;

        if (!target.matches("[data-membership-list]")) {
            return;
        }

        const editor = target.closest(
            "[data-membership-editor]"
        );

        if (!editor) {
            return;
        }

        updateMembershipEmptyState(editor);
        markMembershipDirty(editor);
    }
);
*/
