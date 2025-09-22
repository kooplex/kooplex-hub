// fileresource_selection.js

// FileSystem Resource Selection Modal Logic
class MountHandler {
  constructor(register, opts = {}) {
    this.register = register;
    this.modalSelector     = opts.modalSelector     || '.fileresource-modal';
    this.triggerSelector   = opts.triggerSelector   || 'button[data-pk][data-name=mount]';
    this.confirmSelector   = opts.confirmSelector   || 'button#confirm-file-selection';
    this.toggleSelector    = opts.toggleSelector    || '.configtoggle';
    this.busy = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>Saving...`;

    // state
    this.selectedContainerId = null;
    this.callbackPathOrFn = null;

    // bind
    this._onTriggerClick   = this._onTriggerClick.bind(this);
    this._onConfirmClick   = this._onConfirmClick.bind(this);

    // cache
    this.$modal = $(this.modalSelector);

    this.init();
  }

  init() {
    $(document).on('click', this.triggerSelector, this._onTriggerClick);
    $(document).on('click', this.confirmSelector, this._onConfirmClick);
  }

  destroy() {
    $(document).off('click', this.triggerSelector, this._onTriggerClick);
    $(document).off('click', this.confirmSelector, this._onConfirmClick);
  }

  // Programmatic open
  openModal(containerId) {
    this._open(containerId);
  }

  // ---------------- internals ----------------

  _onTriggerClick(e) {
    const $btn = $(e.currentTarget);
    const containerId = String($btn.data('pk'));
    this._open(containerId);
  }

  _open(containerId) {
    this.selectedContainerId = (containerId === 'None') ? 'None' : parseInt(containerId, 10);

    // reset all toggles OFF
    $(this.toggleSelector).each(function() {
      try { $(this).bootstrapToggle('off'); } catch (_) {}
    });

    // preset togglers from original data arrays
    this._arySet(this._getOriginal(containerId, 'projects'), 'projecttoggler');
    this._arySet(this._getOriginal(containerId, 'courses'),  'coursetoggler');
    this._arySet(this._getOriginal(containerId, 'volumes'),  'volumetoggler');

    // show modal
    this.$modal.modal('show');
  }

  _onConfirmClick(e) {
    if (this.selectedContainerId == null) return;

    const pk = this.selectedContainerId;

    const projects   = $('[name=attach-project]:checked').map(function(){ return parseInt(this.value,10); }).get();
    const courses    = $('[name=attach-course]:checked').map(function(){ return parseInt(this.value,10); }).get();
    const volumes    = $('[name=attach-volume]:checked').map(function(){ return parseInt(this.value,10); }).get();

    const projects_o = this._getOriginal(pk, 'projects');
    const courses_o  = this._getOriginal(pk, 'courses');
    const volumes_o  = this._getOriginal(pk, 'volumes');

    const $btn = $(`${this.triggerSelector}[data-pk="${pk}"]`);
    $btn.html(this.busy).prop('disabled', true);
    try {
        this.register.register_changes(pk, 'projects', projects, projects_o);
        this.register.register_changes(pk, 'courses',  courses,  courses_o);
        this.register.register_changes(pk, 'volumes',  volumes,  volumes_o);
    } catch (err) {
        console.error(err);
        // Basic error hint (replace with your toast)
        $btn.html(`<span class="text-danger">Save failed</span>`).prop('disabled', true);
    } finally {
        this.$modal.modal('hide');
        this.selectedContainerId = null;
    }
  }

  // -------- helpers from original code (polished) --------

  _arySet(arr, togglerPrefix) {
    const list = this._ensureArrayOfInts(arr);
    list.forEach(val => {
      try { $(`#${togglerPrefix}-${val}`).bootstrapToggle('on'); } catch (_) {}
    });
  }

  _getOriginal(pk, binding) {
    const $row = $(`${this.triggerSelector}[data-pk="${pk}"]`);
    const val = $row.data(binding);
    // tolerate strings from data-attrs (e.g., "[1,2,3]")
    if (typeof val === 'string') {
      try { return JSON.parse(val); } catch { /* fallthrough */ }
    }
    return val ?? [];
  }

  _ensureArrayOfInts(val) {
    if (Array.isArray(val)) return val.map(x => parseInt(x,10)).filter(n => !Number.isNaN(n));
    if (val == null || val === '') return [];
    if (typeof val === 'string') {
      try {
        const parsed = JSON.parse(val);
        if (Array.isArray(parsed)) return parsed.map(x => parseInt(x,10)).filter(n => !Number.isNaN(n));
      } catch(_) {}
    }
    return [];
  }

}

