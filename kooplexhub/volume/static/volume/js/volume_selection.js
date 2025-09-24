// volume_selection.js

// Volume Selection Modal Logic
class VolumeHandler {
  constructor(register, opts = {}) {
    this.register = register;
    this.modalSelector   = opts.modalSelector   || '.volumes-modal';
    this.confirmSelector = opts.confirmSelector || '#confirm-file-selection';
    this.toggleSelector  = opts.toggleSelector  || '.configtoggle[name=attach-volume]';
    this.triggerSelector = opts.triggerSelector || '[data-name=volumes][data-pk][data-value][data-model][data-editable=True]'

    this.selectedObjectId = null;
    this.originalVolumes  = []; // array of ints

    // cache
    this.$modal = $(this.modalSelector);

    // bind
    this._onConfirmClick = this._onConfirmClick.bind(this);
    this._onTriggerClick = this._onTriggerClick.bind(this);

    this.init();
  }

  init() {
    $(document).on('click', this.confirmSelector, this._onConfirmClick);
    $(document).on('click', this.triggerSelector, this._onTriggerClick);
  }

  destroy() {
    $(document).off('click', this.confirmSelector, this._onConfirmClick);
    $(document).off('click', this.triggerSelector, this._onTriggerClick);
  }

  // Programmatic open
  openModal(objectId, currentList=[]) {
    this._open(objectId, currentList);
  }

  // ---------------- internals ----------------

  _onTriggerClick(e) {
    e.preventDefault();
    const $btn = $(e.currentTarget);
    const pk = $btn.data('pk');
    const current = $btn.data('value')
    this._open(pk, current);
  }

  _open(objectId, currentList) {
    this.selectedObjectId = objectId === 'None' ? 'None' : parseInt(objectId, 10);
    this.originalVolumes = this._ensureArrayOfInts(currentList);

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

    this.register.register_changes(this.selectedObjectId, 'volumes', volumes, this.originalVolumes);

    this.$modal.modal('hide');
    this.selectedObjectId = null;
    this.originalVolumes = [];
  }

  // -------- helpers --------

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



