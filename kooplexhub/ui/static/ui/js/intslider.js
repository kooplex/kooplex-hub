(function () {
  function updateOutput(input) {
    const outputId = input.dataset.outputId;
    if (!outputId) {
      return;
    }

    const output = document.getElementById(outputId);
    if (!output) {
      return;
    }

    const unit = input.dataset.unit || "";
    output.value = unit
      ? `${input.value} ${unit}`
      : input.value;
  }

  function updateCoupledSlider(input) {
    const wrapper = input.closest("[data-ui-coupled-intslider]");
    if (!wrapper) {
      return;
    }

    const request = wrapper.querySelector(
      '[data-slider-role="request"]'
    );
    const limit = wrapper.querySelector(
      '[data-slider-role="limit"]'
    );

    if (!request || !limit) {
      return;
    }

    const requestValue = Number(request.value);
    const limitValue = Number(limit.value);

    if (input === request && requestValue > limitValue) {
      limit.value = request.value;
      updateOutput(limit);
    }

    if (input === limit && limitValue < requestValue) {
      request.value = limit.value;
      updateOutput(request);
    }
  }

  function handleInput(event) {
    const input = event.target.closest("[data-ui-intslider-input]");
    if (!input) {
      return;
    }

    updateOutput(input);
    updateCoupledSlider(input);
  }

  document.addEventListener("input", handleInput);
})();

