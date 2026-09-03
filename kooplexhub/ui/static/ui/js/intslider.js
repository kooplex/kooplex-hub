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
      clearDefault(limit);
      updateOutput(limit);
    }

    if (input === limit && limitValue < requestValue) {
      request.value = limit.value;
      clearDefault(request);
      updateOutput(request);
    }
  }

  function handleInput(event) {
    const input = event.target.closest("[data-ui-intslider-input]");
    if (!input) {
      return;
    }

    clearDefault(input);
    clearCoupledDefaultState(input);
    updateOutput(input);
    updateCoupledSlider(input);
  }

  function setDefault(slider) {
    const flag = slider.querySelector(
      "[data-ui-intslider-default-flag]"
    );
  
    if (!flag) {
      return;
    }
  
    flag.value = "1";
    slider.classList.add("ui-intslider--default");
  }
  
  function clearDefault(input) {
    const slider = input.closest("[data-ui-intslider]");
    if (!slider) {
      return;
    }
  
    const flag = slider.querySelector(
      "[data-ui-intslider-default-flag]"
    );
  
    if (flag) {
      flag.value = "0";
    }
  
    slider.classList.remove("ui-intslider--default");
  }

  function clearCoupledDefaultState(input) {
    const coupled = input.closest("[data-ui-coupled-intslider]");
    if (!coupled) {
      return;
    }
  
    if (input.dataset.sliderRole === "limit") {
      const request = coupled.querySelector(
        '[data-slider-role="request"]'
      );
  
      if (request) {
        clearDefault(request);
      }
    }
  }
  
  function handleClick(event) {
    const button = event.target.closest(
      "[data-ui-intslider-default]"
    );
  
    if (!button) {
      return;
    }
  
    const slider = button.closest("[data-ui-intslider]");
    if (!slider) {
      return;
    }
  
    const coupled = slider.closest("[data-ui-coupled-intslider]");
    const input = slider.querySelector(
      "[data-ui-intslider-input]"
    );
    const role = input?.dataset.sliderRole;
  
    setDefault(slider);
  
    if (coupled && role === "request") {
      const limitInput = coupled.querySelector(
        '[data-slider-role="limit"]'
      );
      const limitSlider = limitInput?.closest("[data-ui-intslider]");
  
      if (limitSlider) {
        setDefault(limitSlider);
      }
    }
  }


  document.addEventListener("input", handleInput);
  document.addEventListener("click", handleClick);
})();

