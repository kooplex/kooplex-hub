function initializeAssignmentCreateWizard(form) {
    if (form._assignmentWizard) {
        return;
    }

    const steps = Array.from(
        form.querySelectorAll(
            "[data-assignment-wizard-step]"
        )
    );

    const previous = form.querySelector(
        "[data-assignment-wizard-previous]"
    );

    const next = form.querySelector(
        "[data-assignment-wizard-next]"
    );

    const createButtons = Array.from(
        form.querySelectorAll(
            "[data-assignment-create], " +
            "[data-assignment-create-handout]"
        )
    );

    let currentStep = 0;

    function generalIsValid() {
        const folder =
            form.elements.namedItem("folder");

        const name =
            form.elements.namedItem("name");

        const description =
            form.elements.namedItem(
                "description"
            );

        return Boolean(
            folder?.value
            && name?.value.trim()
            && description?.value.trim()
        );
    }

    function updateActions() {
        const valid = generalIsValid();

        for (const button of createButtons) {
            button.disabled = !valid;
        }

        previous.hidden = (
            currentStep === 0
        );

        next.hidden = (
            currentStep === steps.length - 1
        );
    }

    function showStep(index) {
        currentStep = index;

        for (const step of steps) {
            step.hidden = (
                Number(
                    step.dataset
                        .assignmentWizardStep
                )
                !== currentStep
            );
        }

        updateActions();
    }

    form.addEventListener(
        "input",
        updateActions,
    );

    form.addEventListener(
        "change",
        updateActions,
    );

    next?.addEventListener(
        "click",
        () => showStep(1),
    );

    previous?.addEventListener(
        "click",
        () => showStep(0),
    );

    form._assignmentWizard = true;

    showStep(0);
}


function initializeAssignmentCreateWizards(
    root
) {
    if (
        root.matches?.(
            "[data-assignment-create-wizard]"
        )
    ) {
        initializeAssignmentCreateWizard(
            root
        );
    }

    root.querySelectorAll?.(
        "[data-assignment-create-wizard]"
    ).forEach(
        initializeAssignmentCreateWizard
    );
}


document.addEventListener(
    "DOMContentLoaded",
    () => {
        initializeAssignmentCreateWizards(
            document
        );
    },
);


document.body.addEventListener(
    "htmx:afterSwap",
    event => {
        initializeAssignmentCreateWizards(
            event.detail.target
        );
    },
);
