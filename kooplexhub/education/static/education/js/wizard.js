function initializeCourseCreateWizard(form) {
    if (form._courseWizard) {
        return;
    }

    const steps = Array.from(
        form.querySelectorAll("[data-wizard-step]")
    );

    const navigationButtons = Array.from(
        form.querySelectorAll("[data-wizard-go]")
    );

    const previousButton = form.querySelector(
        "[data-wizard-previous]"
    );

    const nextButton = form.querySelector(
        "[data-wizard-next]"
    );

    const createButton = form.querySelector(
        "[data-wizard-create]"
    );
    
    const createEnvironmentButton = form.querySelector(
        "[data-wizard-create-environment]"
    );

    const preferredImageSelect = form.querySelector(
        'select[name="preferred_image"]'
    );

    let currentStep = 0;
    let pendingStep = null;
    let imageNavigationPending = false;

    const generalValidation = {
        name: false,
        description: false,
    };

    function completeGeneralValidation(
        fieldName
    ) {
        generalValidation[fieldName] = true;
    
        if (
            !generalValidation.name
            || !generalValidation.description
        ) {
            return;
        }
    
        if (pendingStep === null) {
            return;
        }
    
        const targetStep = pendingStep;
        pendingStep = null;
    
        showStep(targetStep);
    }

    function completeImageValidation() {
        updateCreateActions();

        if (!imageNavigationPending) {
            return;
        }

        imageNavigationPending = false;

        if (pendingStep === null) {
            return;
        }

        const targetStep = pendingStep;
        pendingStep = null;

        showStep(targetStep);
    }

    form.addEventListener(
        "change",
        event => {
            if (
                !event.target.matches(
                    'select[name="preferred_image"]'
                )
            ) {
                return;
            }
    
            updateCreateActions();
    
            if (event.target.value) {
                imageNavigationPending = false;
                pendingStep = null;

                validatePreferredImage(form);
            }
        },
    );

    function getPreferredImageSelect() {
        return form.querySelector(
            'select[name="preferred_image"]'
        );
    }
    
    function hasSelectedPreferredImage() {
        return Boolean(
            getPreferredImageSelect()?.value
        );
    }

    function updateCreateActions() {
        const imageSelected =
            hasSelectedPreferredImage();
    
        if (createButton) {
            createButton.hidden =
                !imageSelected;
        }
    
        if (createEnvironmentButton) {
            createEnvironmentButton.hidden =
                !imageSelected;
        }
    }

    function showStep(stepIndex) {
        currentStep = stepIndex;

        for (const step of steps) {
            step.hidden = (
                Number(step.dataset.wizardStep)
                !== currentStep
            );
        }

        for (const button of navigationButtons) {
            const active = (
                Number(button.dataset.wizardGo)
                === currentStep
            );

            button.classList.toggle(
                "active",
                active,
            );

            if (active) {
                button.setAttribute(
                    "aria-current",
                    "step",
                );
            } else {
                button.removeAttribute(
                    "aria-current",
                );
            }
        }

        if (previousButton) {
            previousButton.hidden = (
                currentStep === 0
            );
        }

        if (nextButton) {
            nextButton.hidden = (
                currentStep === steps.length - 1
            );
        }

        updateCreateActions();
    }

    function requestStep(targetStep) {
        if (
            currentStep === 0
            && targetStep > 0
        ) {
            pendingStep = targetStep;

            generalValidation.name = false;
            generalValidation.description = false;

            validateCourseName(form);
            validateCourseDescription(form);
            return;
        }

        if (
            currentStep === 1
            && targetStep > 1
        ) {
            pendingStep = targetStep;
            imageNavigationPending = true;

            validatePreferredImage(form);
            return;
        }

        showStep(targetStep);
    }

    if (nextButton) {
        nextButton.addEventListener(
            "click",
            () => {
                requestStep(
                    Math.min(
                        currentStep + 1,
                        steps.length - 1,
                    )
                );
            },
        );
    }

    if (previousButton) {
        previousButton.addEventListener(
            "click",
            () => {
                requestStep(
                    Math.max(
                        currentStep - 1,
                        0,
                    )
                );
            },
        );
    }

    for (const button of navigationButtons) {
        button.addEventListener(
            "click",
            () => {
                requestStep(
                    Number(button.dataset.wizardGo)
                );
            },
        );
    }

    preferredImageSelect?.addEventListener(
        "change",
        () => {
            updateCreateActions();
        },
    );

    form._courseWizard = {
        completeNameValidation() {
            completeGeneralValidation("name");
        },
    
        completeDescriptionValidation() {
            completeGeneralValidation(
                "description"
            );
        },

        completeImageValidation,
    };

    showStep(0);
}

function validateCourseName(form) {
    const url = form.dataset.nameValidationUrl;

    const nameField = form.elements.namedItem(
        "name"
    );

    if (!url || !nameField) {
        return;
    }

    htmx.ajax(
        "POST",
        url,
        {
            source: form,
            target: "#course-create-name-field",
            swap: "outerHTML",
            values: {
                name: nameField.value,
            },
        },
    );
}

function validateCourseDescription(form) {
    const url = form.dataset.descriptionValidationUrl;

    const descriptionField = form.elements.namedItem(
        "description"
    );

    if (!url || !descriptionField) {
        return;
    }

    htmx.ajax(
        "POST",
        url,
        {
            source: form,
            target: "#course-create-description-field",
            swap: "outerHTML",
            values: {
                description: descriptionField.value,
            },
        },
    );
}

function validatePreferredImage(form) {
    const url =
        form.dataset.preferredImageValidationUrl;

    const field = form.elements.namedItem(
        "preferred_image"
    );

    if (!url || !field) {
        return;
    }

    htmx.ajax(
        "POST",
        url,
        {
            source: form,
            target:
                "#course-create-preferred-image-field",
            swap: "outerHTML",
            values: {
                preferred_image: field.value,
            },
        },
    );
}

function initializeCourseCreateWizards(root) {
    if (
        root.matches?.(
            "[data-course-create-wizard]"
        )
    ) {
        initializeCourseCreateWizard(root);
    }

    root.querySelectorAll?.(
        "[data-course-create-wizard]"
    ).forEach(
        initializeCourseCreateWizard
    );
}

document.addEventListener(
    "DOMContentLoaded",
    () => {
        initializeCourseCreateWizards(
            document
        );
    },
);

document.body.addEventListener(
    "htmx:afterSwap",
    event => {
        initializeCourseCreateWizards(
            event.detail.target
        );
    },
);

document.body.addEventListener(
    "course-create-name-valid",
    () => {
        const form = document.querySelector(
            "[data-course-create-wizard]"
        );

        form?._courseWizard
            ?.completeNameValidation();
    },
);

document.body.addEventListener(
    "course-create-description-valid",
    () => {
        const form = document.querySelector(
            "[data-course-create-wizard]"
        );

        form?._courseWizard
            ?.completeDescriptionValidation();
    },
);

document.body.addEventListener(
    "course-create-image-valid",
    () => {
        const form = document.querySelector(
            "[data-course-create-wizard]"
        );

        form?._courseWizard
            ?.completeImageValidation();
    },
);
