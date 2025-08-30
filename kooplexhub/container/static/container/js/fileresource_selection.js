// fileresource_selection.js

// FileSystem Resource Selection Modal Logic
class MountHandler {
  /**
   * @param {Object} opts
   * @param {string} [opts.modalSelector='.fileresource-modal']
   * @param {string} [opts.triggerSelector='button[name=mount][data-id]']
   * @param {string} [opts.confirmSelector='button#confirm-file-selection']
   * @param {string} [opts.toggleSelector='.configtoggle']
   * @param {string} [opts.mountRowSelector='[name=mount][data-id]']
   */
  constructor(opts = {}) {
    this.modalSelector     = opts.modalSelector     || '.fileresource-modal';
    this.triggerSelector   = opts.triggerSelector   || 'button[name=mount][data-id]';
    this.confirmSelector   = opts.confirmSelector   || 'button#confirm-file-selection';
    this.toggleSelector    = opts.toggleSelector    || '.configtoggle';
    this.mountRowSelector  = opts.mountRowSelector  || '[name=mount][data-id]';

    // state
    this.selectedContainerId = null;
    this.callbackPathOrFn = null;

    // bind
    this._onTriggerClick   = this._onTriggerClick.bind(this);
    this._onConfirmClick   = this._onConfirmClick.bind(this);

    // cache
    this.$modal = $(this.modalSelector);
  }

  init() {
    $(document).on('mouseenter', this.triggerSelector, function () {
      $(this).css('cursor', 'pointer');
    });
    $(document).on('click', this.triggerSelector, this._onTriggerClick);
    $(document).on('click', this.confirmSelector, this._onConfirmClick);
  }

  destroy() {
    $(document).off('mouseenter', this.triggerSelector);
    $(document).off('click', this.triggerSelector, this._onTriggerClick);
    $(document).off('click', this.confirmSelector, this._onConfirmClick);
  }

  // Programmatic open
  openModal(containerId, callbackPathOrFn = null) {
    this._open(containerId, callbackPathOrFn);
  }

  // ---------------- internals ----------------

  _onTriggerClick(e) {
    const $btn = $(e.currentTarget);
    const containerId = String($btn.data('id'));
    const cb = $btn.data('callback'); // e.g., "wss_containerconfig.registerchanges"
    this._open(containerId, cb);
  }

  _open(containerId, callbackPathOrFn) {
    this.selectedContainerId = (containerId === 'None') ? 'None' : parseInt(containerId, 10);
    this.callbackPathOrFn = callbackPathOrFn || null;

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

    // overwrite originals in DOM dataset
    this._overwriteOriginal(pk, 'projects', projects);
    this._overwriteOriginal(pk, 'courses',  courses);
    this._overwriteOriginal(pk, 'volumes',  volumes);

    // resolve saver and per-call callback
    const cb    = this._resolveFn(this.callbackPathOrFn); // bound if it's a method path

    let c1=false, c2=false, c3=false;
    if (typeof cb === 'function') {
      // keep API compatible; pass callback as 5th arg if saver accepts it (extra args are ignored if not used)
      c1 = !!cb(pk, 'projects', projects, projects_o);
      c2 = !!cb(pk, 'courses',  courses,  courses_o);
      c3 = !!cb(pk, 'volumes',  volumes,  volumes_o);
    } else {
      console.warn('MountHandler: no save function (register_changes) found.');
    }

    if (c1 || c2 || c3) {
      this._updateButtonFace(pk, projects.length, courses.length, volumes.length);
    }

    // close modal & reset state
    this.$modal.modal('hide');
    this.selectedContainerId = null;
  }

  // -------- helpers from original code (polished) --------

  _arySet(arr, togglerPrefix) {
    const list = this._ensureArrayOfInts(arr);
    list.forEach(val => {
      try { $(`#${togglerPrefix}-${val}`).bootstrapToggle('on'); } catch (_) {}
    });
  }

  _getOriginal(pk, binding) {
    const $row = $(`${this.mountRowSelector}[data-id="${pk}"]`);
    const val = $row.data(binding);
    // tolerate strings from data-attrs (e.g., "[1,2,3]")
    if (typeof val === 'string') {
      try { return JSON.parse(val); } catch { /* fallthrough */ }
    }
    return val ?? [];
  }

  _overwriteOriginal(pk, binding, value) {
    const $row = $(`${this.mountRowSelector}[data-id="${pk}"]`);
    $row.data(binding, value);
  }

  _updateButtonFace(pk, p, c, v) {
    const base = `${this.mountRowSelector}[data-id="${pk}"]`;
    $(`${base} [name=project_count]`).text(p);
    $(`${base} [name=course_count]`).text(c);
    $(`${base} [name=volume_count]`).text(v);

    const $wid_project = $(`${base} [name=project]`);
    const $wid_course  = $(`${base} [name=course]`);
    const $wid_volume  = $(`${base} [name=volume]`);
    const $wid_empty   = $(`${base} [name=empty]`);

    (p===0) ? $wid_project.addClass('d-none') : $wid_project.removeClass('d-none');
    (c===0) ? $wid_course .addClass('d-none') : $wid_course .removeClass('d-none');
    (v===0) ? $wid_volume .addClass('d-none') : $wid_volume .removeClass('d-none');
    ((p+c+v)===0) ? $wid_empty.removeClass('d-none') : $wid_empty.addClass('d-none');
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

  _resolveFn(pathOrFn) {
    if (!pathOrFn) return null;
    if (typeof pathOrFn === 'function') return pathOrFn;

    if (typeof pathOrFn === 'string') {
      const parts = pathOrFn.split('.');
      const method = parts.pop();
      const ctx = parts.reduce((acc, key) => (acc ? acc[key] : undefined), window);
      const fn = ctx?.[method];
      if (typeof fn === 'function') return fn.bind(ctx);
    }
    return null;
  }
}



// Run when document is ready
$(document).ready(function() {
  const mountHandler = new MountHandler();
  mountHandler.init();
});


