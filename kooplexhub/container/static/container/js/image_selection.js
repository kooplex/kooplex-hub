// image_selection.js

// Image Selection Modal Logic
class ImageSelectionHandler {
  constructor(register, opts = {}) {
    this.register = register;
    this.modalSelector = opts.modalSelector || '.image-modal';
    this.listSelector = opts.listSelector || '#image-list';
    this.itemSelector = opts.itemSelector || '.image-item';
    this.confirmSelector = opts.confirmSelector || '#confirm-image-selection';
    this.alertSelector = opts.alertSelector || '#imageModalAlert';
    this.previewNameSelector = opts.previewNameSelector || '#image-name';
    this.previewDescSelector = opts.previewDescSelector || '#image-description';
    this.previewThumbSelector = opts.previewThumbSelector || '#image-thumbnail';
    this.triggerSelector = opts.triggerSelector || 'button[data-pk][data-field=image]';
    this.busy = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>Saving...`;

    // State
    this.selectedObjectId = null;
    this.selectedImageId = null;
    this.originalImageId = null;
    this.selectedIndex = -1;
    this.targetAttribute = 'image';

    // Cache
    this.$modal = $(this.modalSelector);
    this.$list = $(this.listSelector);

    // Bind handlers
    this._onItemClick = this._onItemClick.bind(this);
    this._onKeyDown = this._onKeyDown.bind(this);
    this._onConfirm = this._onConfirm.bind(this);
    this._onTriggerClick = this._onTriggerClick.bind(this);

    this.init();
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
  openModal(pk, imageSelectedId, attribute = 'image') {
    this._openModalInternal(pk, imageSelectedId, attribute);
  }

  // ---------------- Internals ----------------

  _onTriggerClick(e) {
    const $btn = $(e.currentTarget);
    const pk = String($btn.data('pk'));
    const imageSelectedId = $btn.data('orig');
    const attr = $btn.data('name');
    this._openModalInternal(pk, imageSelectedId, attr);
  }

  _openModalInternal(pk, imageSelectedId, attribute) {
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

  _onConfirm(el) {
    const $btn = $(el.currentTarget);
    if (this.selectedObjectId != null && this.selectedImageId) {
      const field = this.targetAttribute;
      const newVal = this.selectedImageId;
      const oldVal = this.originalImageId;
      const $widget = $(`button[data-name=${field}][data-pk="${this.selectedObjectId}"]`);
      try {
        this.register.register_changes(this.selectedObjectId, field, newVal, this.oldValue);
        // Update UI with returned value (or the submitted one)
        $widget.html(this.busy).prop('disabled', true);
      } catch (err) {
        console.error(err);
        // Basic error hint (replace with your toast)
        $widget.html(`<span class="text-danger">Save failed</span>`).prop('disabled', true);
      } finally {
        this.$modal.modal('hide');
      }
    }
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

}


