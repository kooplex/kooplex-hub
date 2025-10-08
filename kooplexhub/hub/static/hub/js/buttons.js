// toggle button
class ToggleButton {
  constructor(register, opts = {}) {
    this.register = register;
    this.buttonSelector = opts.buttonSelector || 'button[data-pk][data-value]';
    this.busy = `<span class="spinner-border spinner-border-sm text-dark" role="status" aria-hidden="true"></span>`;

    this._onButtonClick = this._onButtonClick.bind(this);

    this.init();
  }

  init() {
    // Delegate the event to the document for dynamic elements
    $(document).on('click', this.buttonSelector, this._onButtonClick);
  }

  destroy() {
    $(document).off('click', this.buttonSelector, this._onButtonClick);
  }

  _onButtonClick(event) {
    const $button = $(event.currentTarget);
    const pk = $button.data('pk');
    const field = $button.data('name');
    const newValue = ! ($button.data('value') || false);
    this.register.register_changes(pk, field, newValue, ! newValue);
    this._setBusyState($button);
  }

  _setBusyState($button) {
    const originalContent = $button.html();
    $button.html(`${this.busy}`);
    $button.prop('disabled', true);
  }
}

// hover dropdown button
class HoverDropDown {
  constructor() {
    this.showTimer;
    this.hideTimer;
    this._dropdown = this._dropdown.bind(this);
    this._collapse = this._collapse.bind(this);
    this._freeze = this._freeze.bind(this);
    this._hide = this._hide.bind(this);
    this.init();
  }

  init() {
    $(document).on("mouseenter", ".hover-dropdown", this._dropdown);
    $(document).on("mouseleave", ".hover-dropdown", this._collapse);
    $(document).on("mouseenter", ".dropdown-content", this._freeze);
    $(document).on("mouseleave", ".dropdown-content", this._hide);
  }

  destroy() {
    $(document).off("mouseenter", ".hover-dropdown", this._dropdown);
    $(document).off("mouseleave", ".hover-dropdown", this._collapse);
    $(document).off("mouseenter", ".dropdown-content", this._freeze);
    $(document).off("mouseleave", ".dropdown-content", this._hide);
  }

  _dropdown(event) {
    const $button = $(event.currentTarget);
    let dropdown = $button.find(".dropdown-content");
    clearTimeout(this.hideTimer);
    this.showTimer = setTimeout(() => {
        dropdown.fadeIn(200);
    }, 200);
  }

  _collapse(event) {
    const $button = $(event.currentTarget);
    let dropdown = $button.find(".dropdown-content");

    clearTimeout(this.showTimer);
    this.hideTimer = setTimeout(() => {
        dropdown.fadeOut(200);
    }, 1000);
  }

  _freeze(event) {
    clearTimeout(this.hideTimer);
  }

  _hide(event) {
    const $button = $(event.currentTarget);
    this.hideTimer = setTimeout(() => {
        $button.fadeOut(200);
    }, 1000);
  }
}

// click dropdown button
class DropDown {
  constructor(register, opts = {}) {
    this.register = register;
    this.selector = opts.selector;
    this.field = opts.field;
    this.saveTrigger = opts.saveTrigger || '.dropdown-item';
    this.dummy = opts.dummy || 'None';
    this.pk = null;
    this.oldValue = null;
    this.busy = `<span class="spinner-border spinner-border-sm text-dark" role="status" aria-hidden="true"></span>`;

    this._click = this._click.bind(this);
    this._save = this._save.bind(this);

    this.init();
  }

  init() {
    $(document).on('show.bs.dropdown', this.selector, this._click);
    $(document).on('click', this.saveTrigger, this._save)
  }

  destroy() {
    $(document).off('show.bs.dropdown', this.selector, this._click);
    $(document).off('click', this.saveTrigger, this._save)
  }

  _click(event) {
    const $button = $(event.currentTarget);
    this.oldValue = $button.data('value');
    this.pk = $button.data('pk') || this.dummy;
  }

  _save(event) {
    const $item = $(event.currentTarget);
    const group = $item.closest('.btn-group');
    const btn = group[0] && group[0].querySelector(this.selector); 
    if (!btn) return;
    event.preventDefault();
    const newValue = $item.data('value');
    if (!newValue || newValue === this.oldValue) {
      bootstrap.Dropdown.getOrCreateInstance(btn).hide();
      return;
    }
    btn.innerHTML = this.busy;
    this.register.register_changes(this.pk, this.field, newValue, this.oldValue);
  }
}

