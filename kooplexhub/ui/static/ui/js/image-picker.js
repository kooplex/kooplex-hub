(() => {
    "use strict";

    function updatePreview(select) {
        const picker = select.closest("[data-image-picker]");

        if (!picker) {
            return;
        }

        const value = select.value;

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
    }

    document.addEventListener("change", (event) => {
        const select = event.target.closest(
            "[data-image-picker-select]"
        );

        if (select) {
            updatePreview(select);
        }
    });

    function initialize(root = document) {
        root
            .querySelectorAll("[data-image-picker-select]")
            .forEach(updatePreview);
    }

    document.addEventListener("DOMContentLoaded", () => {
        initialize();
    });

    document.body.addEventListener("htmx:afterSwap", (event) => {
        initialize(event.detail.target);
    });
})();
