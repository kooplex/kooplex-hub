// static/js/volume_selection.js

// Volume Selection Modal Logic
class VolumeHandler {
  /**
   * @param {Object} opts
   * @param {string} [opts.modalSelector='.volumes-modal']
   * @param {string} [opts.confirmSelector='#confirm-file-selection']
   * @param {string} [opts.toggleSelector='.configtoggle[name=attach-volume]']
   * @param {string} [opts.triggerSelector] // optional: e.g. 'button[data-action="edit-volumes"][data-id]'
   */
  constructor(opts = {}) {
    this.modalSelector   = opts.modalSelector   || '.volumes-modal';
    this.confirmSelector = opts.confirmSelector || '#confirm-file-selection';
    this.toggleSelector  = opts.toggleSelector  || '.configtoggle[name=attach-volume]';
    this.triggerSelector = opts.triggerSelector || null;

    this.register = null;
    this.selectedObjectId = null;
    this.originalVolumes  = []; // array of ints

    // cache
    this.$modal = $(this.modalSelector);

    // bind
    this._onConfirmClick = this._onConfirmClick.bind(this);
    this._onTriggerClick = this._onTriggerClick.bind(this);
  }

  init() {
    $(document).on('click', this.confirmSelector, this._onConfirmClick);
    if (this.triggerSelector) {
      $(document).on('click', this.triggerSelector, this._onTriggerClick);
    }
  }

  destroy() {
    $(document).off('click', this.confirmSelector, this._onConfirmClick);
    if (this.triggerSelector) {
      $(document).off('click', this.triggerSelector, this._onTriggerClick);
    }
  }

  // Programmatic open
  openModal(objectId) {
    this._open(objectId);
  }

  // ---------------- internals ----------------

  _onTriggerClick(e) {
    e.preventDefault();
    const $btn = $(e.currentTarget);
    const id = $btn.data('id');
    this.register = $btn.data('callback');
    this._open(id);
  }

  _open(objectId) {
    this.selectedObjectId = objectId === 'None' ? 'None' : parseInt(objectId, 10);

    // Read current/original volumes from any element that carries both data-id and data-volumes
    const $src = $(`[data-id="${this.selectedObjectId}"][data-volumes]`).first();
    this.originalVolumes = this._ensureArrayOfInts($src.data('volumes'));

    // Initialize all toggles OFF then set according to originals
    const self = this;
    $(this.toggleSelector).each(function () {
      const $tog = $(this);
      const pk = parseInt($tog.val(), 10);
      try { $tog.bootstrapToggle(); } catch (_) {}
      if (self.originalVolumes.includes(pk)) {
        $tog.bootstrapToggle('on');
      } else {
        $tog.bootstrapToggle('off');
      }
    });

    this.$modal.modal('show');
  }

  _onConfirmClick(e) {
    if (!this.selectedObjectId) return;

    const volumes = $('[name=attach-volume]:checked')
      .map(function () { return parseInt(this.value, 10); })
      .get();

    let changed = false;
    const saver = this._resolveSaveFn(this.register);
    if (typeof saver === 'function') {
      saver(this.selectedObjectId, 'volumes', volumes, this.originalVolumes);
    } else {
      console.warn('VolumeHandler: register_changes not found');
    }

    this.$modal.modal('hide');
    this.selectedObjectId = null;
    this.originalVolumes = [];
  }

  // -------- helpers --------

  _resolveSaveFn(pathOrFn) {
    if (!pathOrFn) return null;
    if (typeof pathOrFn === 'function') return pathOrFn;
    if (typeof pathOrFn === 'string') {
      // Resolve "obj.method" safely
      const parts = pathOrFn.split('.');
      const method = parts.pop();
      const ctx = parts.reduce((acc, key) => (acc ? acc[key] : undefined), window);
      const fn = ctx?.[method];
      if (typeof fn === 'function') {
        // bind to ctx so `this` works for instance methods
        return fn.bind(ctx);
      }
    }
    return null;
  }



  _ensureArrayOfInts(val) {
    if (Array.isArray(val)) {
      return val.map(x => parseInt(x, 10)).filter(n => !Number.isNaN(n));
    }
    if (val == null || val === '') return [];
    if (typeof val === 'string') {
      try {
        const parsed = JSON.parse(val);
        if (Array.isArray(parsed)) {
          return parsed.map(x => parseInt(x, 10)).filter(n => !Number.isNaN(n));
        }
      } catch (_) {}
    }
    // jQuery may give a scalar for data-volumes="3" — normalize
    const n = parseInt(val, 10);
    return Number.isNaN(n) ? [] : [n];
  }
}



// Run when document is ready
$(document).ready(function() {
  const vh = new VolumeHandler({
    triggerSelector: '[name=volumes][data-id][data-volumes][data-bind][data-callback]'
  });
  vh.init();
})
