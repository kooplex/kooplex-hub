(() => {
  "use strict";

  const WIZARD_SELECTOR =
    "[data-container-create-wizard]";

  const STEP_SELECTOR =
    "[data-container-wizard-step]";

  function findWizards(root = document) {
    const result = [];

    if (
      root.matches &&
      root.matches(WIZARD_SELECTOR)
    ) {
      result.push(root);
    }

    if (root.querySelectorAll) {
      root
        .querySelectorAll(WIZARD_SELECTOR)
        .forEach((wizard) => {
          result.push(wizard);
        });
    }

    return result;
  }

  function getSteps(wizard) {
    return Array.from(
      wizard.querySelectorAll(
        STEP_SELECTOR
      )
    );
  }

  function currentStep(wizard) {
    return Number(
      wizard.dataset.currentStep ??
      wizard.dataset.initialStep ??
      0
    );
  }

  function renderWizard(
    wizard,
    step,
  ) {
    const steps = getSteps(wizard);

    if (!steps.length) {
      return;
    }

    step = Math.max(
      0,
      Math.min(
        step,
        steps.length - 1,
      ),
    );

    wizard.dataset.currentStep =
      String(step);

    steps.forEach(
      (element, index) => {
        element.hidden =
          index !== step;
      },
    );

    wizard
      .querySelectorAll(
        "[data-wizard-indicator]"
      )
      .forEach((indicator) => {
        const index = Number(
          indicator.dataset
            .wizardIndicator
        );

        indicator.classList.toggle(
          "active",
          index === step,
        );

        indicator.classList.toggle(
          "completed",
          index < step,
        );
      });

    const back = wizard.querySelector(
      "[data-container-wizard-back]"
    );

    const next = wizard.querySelector(
      "[data-container-wizard-next]"
    );

    const submit =
      wizard.querySelector(
        "[data-container-wizard-submit]"
      );

    if (back) {
      back.hidden = step === 0;
    }

    if (next) {
      next.hidden =
        step === steps.length - 1;
    }

  }

  function validateGeneralStep(
    wizard,
  ) {
    const name = wizard.querySelector(
      '[name="name"]'
    );

    if (
      name &&
      !name.checkValidity()
    ) {
      name.reportValidity();
      return false;
    }

    /*
     * Works regardless of whether image is
     * represented later as:
     *
     *   <select>
     *   hidden input
     *   radio buttons
     *
     * This is useful while we converge the
     * image picker.
     */
    const data = new FormData(wizard);
    const image = data.get("image");

    if (!image) {
      const picker =
        wizard.querySelector(
          "[data-image-picker]"
        );

      if (picker) {
        picker.classList.add(
          "border",
          "border-danger",
          "rounded",
          "p-2",
        );
      }

      const firstImageControl =
        wizard.querySelector(
          '[name="image"]'
        );

      firstImageControl?.focus();

      return false;
    }

    return true;
  }

  function initialize(
    root = document,
  ) {
    findWizards(root).forEach(
      (wizard) => {
        if (
          wizard.dataset
            .wizardInitialized
        ) {
          return;
        }

        wizard.dataset
          .wizardInitialized = "1";

        renderWizard(
          wizard,
          Number(
            wizard.dataset
              .initialStep || 0
          ),
        );
      },
    );
  }

  /*
   * Delegated navigation.
   *
   * This keeps working even when the
   * entire modal is replaced by HTMX.
   */
  document.addEventListener(
    "click",
    (event) => {
      const next =
        event.target.closest(
          "[data-container-wizard-next]"
        );

      if (next) {
        const wizard =
          next.closest(
            WIZARD_SELECTOR
          );

        if (!wizard) {
          return;
        }

        const step =
          currentStep(wizard);

        if (
          step === 0 &&
          !validateGeneralStep(
            wizard
          )
        ) {
          return;
        }

        renderWizard(
          wizard,
          step + 1,
        );

        return;
      }

      const back =
        event.target.closest(
          "[data-container-wizard-back]"
        );

      if (back) {
        const wizard =
          back.closest(
            WIZARD_SELECTOR
          );

        if (!wizard) {
          return;
        }

        renderWizard(
          wizard,
          currentStep(wizard) - 1,
        );
      }
    },
  );

  document.addEventListener(
    "DOMContentLoaded",
    () => {
      initialize(document);
    },
  );

  document.body.addEventListener(
    "htmx:afterSwap",
    (event) => {
      initialize(
        event.detail.target
      );
    },
  );

  function validateGeneralStep(
    wizard,
  ) {
    const name = wizard.querySelector(
      '[name="name"]'
    );
  
    if (
      !name ||
      !name.value.trim()
    ) {
      renderWizard(
        wizard,
        0,
      );
  
      name?.setCustomValidity(
        "Please enter an environment name."
      );
  
      name?.reportValidity();
  
      name?.setCustomValidity("");
  
      return false;
    }
  
    const image = new FormData(
      wizard
    ).get("image");
  
    if (!image) {
      renderWizard(
        wizard,
        0,
      );
  
      const picker =
        wizard.querySelector(
          "[data-image-picker]"
        );
  
      picker?.classList.add(
        "border",
        "border-danger",
        "rounded",
        "p-2",
      );
  
      return false;
    }
  
    return true;
  }

  document.addEventListener(
    "click",
    (event) => {
      const submit =
        event.target.closest(
          "[data-container-wizard-submit]"
        );
  
      if (!submit) {
        return;
      }
  
      const wizard =
        submit.closest(
          "[data-container-create-wizard]"
        );
  
      if (!wizard) {
        return;
      }
  
      if (!validateGeneralStep(wizard)) {
        event.preventDefault();
  
        renderWizard(
          wizard,
          0,
        );
      }
    },
  );
})();


