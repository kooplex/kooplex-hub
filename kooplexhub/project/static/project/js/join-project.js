(function () {
  document.body.addEventListener("input", event => {
    if (!event.target.matches(
      "[data-project-join-filter]"
    )) {
      return;
    }

    const query = (
      event.target.value
      .trim()
      .toLowerCase()
    );

    const modal = event.target.closest(".modal");

    modal
      ?.querySelectorAll(
        "[data-project-join-option]"
      )
      .forEach(option => {
        const text = (
          option.dataset.filterText
          || ""
        ).toLowerCase();

        option.hidden = (
          query
          && !text.includes(query)
        );
      });
  });
})();

(function () {
  document.body.addEventListener(
    "change",
    event => {
      if (
        !event.target.matches(
          "[data-project-join-choice]"
        )
      ) {
        return;
      }

      const form = event.target.closest("form");

      const submitButton = form?.querySelector(
        "[data-project-join-submit]"
      );

      if (submitButton) {
        submitButton.disabled = false;
      }
    },
  );
})();
