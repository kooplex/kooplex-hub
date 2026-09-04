(function () {
  function updatePicker(picker, value) {
    const select = picker.querySelector(
      "[data-image-picker-select]"
    );

    if (!select) {
      return;
    }

    select.value = value;

    picker
      .querySelectorAll("[data-image-picker-item]")
      .forEach((item) => {
        const selected = item.dataset.value === value;

        item.classList.toggle("is-selected", selected);
        item.setAttribute(
          "aria-selected",
          selected ? "true" : "false"
        );
      });

    picker
      .querySelectorAll("[data-image-preview-value]")
      .forEach((preview) => {
        preview.hidden =
          preview.dataset.imagePreviewValue !== value;
      });

    const empty = picker.querySelector(
      "[data-image-picker-empty]"
    );

    if (empty) {
      empty.hidden = Boolean(value);
    }

    select.dispatchEvent(
      new Event("change", { bubbles: true })
    );
  }

  document.addEventListener("click", (event) => {
    const item = event.target.closest(
      "[data-image-picker-item]"
    );

    if (!item) {
      return;
    }

    const picker = item.closest(
      "[data-image-picker]"
    );

    if (!picker) {
      return;
    }

    updatePicker(
      picker,
      item.dataset.value
    );
  });
})();
