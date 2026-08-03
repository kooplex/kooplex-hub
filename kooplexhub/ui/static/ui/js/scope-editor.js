(function () {
  function submitScopeEditor(input) {
    const form = input.closest("[data-scope-editor]");

    if (!form) {
      return;
    }

    htmx.trigger(form, "submit");
  }

  function cancelScopeEditor(form) {
    const cancelUrl = form.dataset.cancelUrl;

    if (!cancelUrl) {
      return;
    }

    htmx.ajax("GET", cancelUrl, {
      source: form,
      target: `#${form.id}`,
      swap: "outerHTML",
    });
  }

  document.body.addEventListener("change", event => {
    const input = event.target.closest(
      "[data-scope-choice]"
    );

    if (!input) {
      return;
    }

    submitScopeEditor(input);
  });

  document.body.addEventListener("keydown", event => {
    if (event.key !== "Escape") {
      return;
    }

    const form = event.target.closest(
      "[data-scope-editor]"
    );

    if (!form) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    cancelScopeEditor(form);
  });
})();


document.body.addEventListener(
  "htmx:afterSwap",
  event => {
    const form = event.detail.target.matches?.(
      "[data-scope-editor]"
    )
      ? event.detail.target
      : event.detail.target.querySelector?.(
          "[data-scope-editor]"
        );

    if (!form) {
      return;
    }

    const selected = form.querySelector(
      "[data-scope-choice]:checked"
    );

    selected?.focus();
  },
);
