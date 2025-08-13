// static/js/image_selection.js

// Image Selection Modal Logic

class ImageSelectionHandler {
  /**
   * @param {Object} opts
   * @param {string} [opts.modalSelector='.image-modal']
   * @param {string} [opts.listSelector='#image-list']
   * @param {string} [opts.itemSelector='.image-item']
   * @param {string} [opts.confirmSelector='#confirm-image-selection']
   * @param {string} [opts.alertSelector='#imageModalAlert']
   * @param {string} [opts.previewNameSelector='#image-name']
   * @param {string} [opts.previewDescSelector='#image-description']
   * @param {string} [opts.previewThumbSelector='#image-thumbnail']
   * @param {string} [opts.triggerSelector='button[data-id][data-field=image]']  // buttons that open the modal
   */
  constructor(opts = {}) {
    this.modalSelector = opts.modalSelector || '.image-modal';
    this.listSelector = opts.listSelector || '#image-list';
    this.itemSelector = opts.itemSelector || '.image-item';
    this.confirmSelector = opts.confirmSelector || '#confirm-image-selection';
    this.alertSelector = opts.alertSelector || '#imageModalAlert';
    this.previewNameSelector = opts.previewNameSelector || '#image-name';
    this.previewDescSelector = opts.previewDescSelector || '#image-description';
    this.previewThumbSelector = opts.previewThumbSelector || '#image-thumbnail';
    this.triggerSelector = opts.triggerSelector || 'button[data-id][data-field=image]';

    // State
    this.selectedObjectId = null;
    this.selectedImageId = null;
    this.originalImageId = null;
    this.selectedIndex = -1;
    this.targetAttribute = 'image';
    this.callbackPathOrFn = null;

    // Cache
    this.$modal = $(this.modalSelector);
    this.$list = $(this.listSelector);

    // Bind handlers
    this._onItemClick = this._onItemClick.bind(this);
    this._onKeyDown = this._onKeyDown.bind(this);
    this._onConfirm = this._onConfirm.bind(this);
    this._onTriggerClick = this._onTriggerClick.bind(this);
  }

  init() {
    // Click on selectable items (delegated)
    $(document).on('click', this.itemSelector, this._onItemClick);
    // Key nav on the scrollable list
    this.$list.on('keydown', this._onKeyDown);
    // Confirm button
    $(document).on('click', this.confirmSelector, this._onConfirm);
    // Buttons that open the modal
    $(document).on('click', this.triggerSelector, this._onTriggerClick);
  }

  destroy() {
    $(document).off('click', this.itemSelector, this._onItemClick);
    this.$list.off('keydown', this._onKeyDown);
    $(document).off('click', this.confirmSelector, this._onConfirm);
    $(document).off('click', this.triggerSelector, this._onTriggerClick);
  }

  // Public API to open the modal programmatically
  openModal(pk, imageSelectedId, attribute = 'image', callbackPathOrFn = null) {
    this._openModalInternal(pk, imageSelectedId, attribute, callbackPathOrFn);
  }

  // ---------------- Internals ----------------

  _onTriggerClick(e) {
    const $btn = $(e.currentTarget);
    const pk = String($btn.data('id'));
    const imageSelectedId = $btn.data('orig');
    const cb = $btn.data('callback');
    this._openModalInternal(pk, imageSelectedId, 'image', cb);
  }

  _openModalInternal(pk, imageSelectedId, attribute, callbackPathOrFn) {
    this.callbackPathOrFn = callbackPathOrFn || null;
    this.selectedObjectId = pk === 'None' ? 'None' : parseInt(pk, 10);
    this.targetAttribute = attribute || 'image';
    this.originalImageId = imageSelectedId || null; // remember original
    this.selectedImageId = null; // will be set on select

    this.$modal.modal('show');

    // Focus/select appropriate item after modal shows
    setTimeout(() => {
      let $item = $(`${this.itemSelector}[data-id="${CSS.escape(String(imageSelectedId || ''))}"]`);
      if ($item.length === 0) {
        $item = $(this.itemSelector).first();
        this.selectedIndex = 0;
        if (pk !== 'None') {
          $(this.alertSelector).removeClass('d-none');
        }
      } else {
        this.selectedIndex = $item.index();
        $(this.alertSelector).addClass('d-none');
      }
      $item.focus();
      this._selectImage(this.selectedIndex);
    }, 200);
  }

  _onItemClick(e) {
    const $item = $(e.currentTarget);
    const index = $item.index();
    this._selectImage(index);
    $item.focus();
  }

  _onKeyDown(e) {
    const total = $(this.itemSelector).length || 0;
    if (!total) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.selectedIndex = (this.selectedIndex + 1) % total;
      this._selectImage(this.selectedIndex);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.selectedIndex = (this.selectedIndex - 1 + total) % total;
      this._selectImage(this.selectedIndex);
    }
  }

  _onConfirm(e) {
    const $btn = $(e.currentTarget);
    if (this.selectedObjectId != null && this.selectedImageId) {
      const field = this.targetAttribute;
      const newVal = this.selectedImageId;
      const oldVal = this.originalImageId;

      const saver = this._resolveSaveFn(this.callbackPathOrFn);
      if (typeof saver === 'function') {
        saver(this.selectedObjectId, field, newVal, oldVal);
        // update label next to the button (customize as needed)
        $(`[data-field=${field}][data-id="${this.selectedObjectId}"]`).text($(this.previewNameSelector).text());
      } else {
        console.warn('No save function resolved for image selection');
      }
    }
    this.$modal.modal('hide');
  }

  _selectImage(index) {
    $(this.itemSelector).removeClass('active');
    const $item = $(this.itemSelector).eq(index);
    $item.addClass('active');

    const id = $item.data('id');
    this.selectedImageId = id;
    this.selectedIndex = index;

    // Right pane preview update
    $(this.previewNameSelector).text($item.text());
    $(this.previewDescSelector).text($item.data('description'));
    $(this.previewThumbSelector).attr('src', $item.data('thumbnail'));

    // Ensure visible
    this._ensureInView($item);
  }

  _ensureInView($el) {
    const $c = this.$list;
    if (typeof $el.position() === 'undefined') return;
    if (!this._isVisibleIn($c, $el)) {
      $c.scrollTop($el.position().top + $c.scrollTop() - $c.height() / 2);
    }
  }

  _isVisibleIn($container, $element) {
    const containerTop = $container.scrollTop();
    const containerBottom = containerTop + $container.height();
    const elementTop = $element.position().top + $container.scrollTop();
    const elementBottom = elementTop + $element.outerHeight();
    return elementTop >= containerTop && elementBottom <= containerBottom;
  }

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
}




// Run when document is ready
$(document).ready(function() {
    const imgSel = new ImageSelectionHandler({});
    imgSel.init();
});



