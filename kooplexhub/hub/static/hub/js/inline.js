class InlineEditor {
  constructor(register, opts = {}) {
    this.register = register;
    this.wrapSelector    = opts.wrapSelector    || '.editable-wrap';
    this.displaySelector = opts.displaySelector || '.editable-display';
    this.revertSelector  = opts.revertSelector  || '.revert-btn';
    this.$active = null;       // jQuery handle to currently-editing display
    this.oldValue = null;      // previous plain value
    this.busy = '<div class="spinner-border" role="status"><span class="visually-hidden">Saving...</span></div>';

    this._bind();
  }

  _bind() {
    $(document).on('click', this.displaySelector, (e) => {
      const $display = $(e.currentTarget);
      if ($display.closest(this.wrapSelector).hasClass('editing')) return;
      e.preventDefault();
      this.startEdit($display);
    });

    $(document).on('click', this.revertSelector, (e) => {
      e.preventDefault();
      const $btn = $(e.currentTarget);
      let $wrap = $btn.data('wrap') ? $($btn.data('wrap')) : $btn.closest(this.wrapSelector);
      if (!$wrap.length) return;
      const original = $btn.data('original') ?? '';
      const type = ($wrap.data('type') || 'text').toLowerCase();
      const $display = $wrap.find(this.displaySelector).first();
      if (!type || type === 'text') {
        $display.text(original);
      } else {
        $display.html(this._br(original));
      }
      $wrap.removeClass('editing');
      this._removePortal($wrap);
    });

    // Click anywhere else closes the portaled error
    $(document).on('click', (e) => {
      const $t = $(e.target);
      if (!$t.closest('.widget-error-portal').length) {
        $('.widget-error-portal').remove();
        $(window).off('.widgetErrPos');
      }
    });
  }

  startEdit($display) {
    if (this.$active) this.cancelEdit(this.$active);
    const $wrap = $display.closest(this.wrapSelector);
    const pk = $wrap.data('pk');
    const type  = ($wrap.data('type') || 'text').toLowerCase();
    const value = pk === "None" ? "" : this._getPlainText($display);
    this.oldValue = value;
    $wrap.addClass('editing');
    this.$active = $display;
    // Build input UI
    const isTA = type === 'textarea';
    const $input = $(isTA ? '<textarea>' : '<input type="text">')
      .addClass(`form-control form-control-sm ${isTA ? 'editable-textarea' : 'editable-input'}`)
      .val(value);

    const $toolbar = $('<div class="editable-toolbar">');
    const $btnSave   = $('<button type="button" class="btn btn-success"><i class="icon-white fas fa-thumbs-up"></i></button>');
    const $btnCancel = $('<button type="button" class="btn btn-danger"><i class="icon-white fas fa-thumbs-down"></i></button>');
    if (isTA) $toolbar.append($btnSave, $btnCancel);
    // stash original html to restore on cancel
    $display.data('origHtml', $display.html());
    $display.empty().append($input);
    if (isTA) $display.append($toolbar);
    $input.trigger('focus');
    if (!isTA) $input[0].select();
    // keyboard shortcuts
    $input.on('keydown', (ev) => {
      if (!isTA && ev.key === 'Enter') { ev.preventDefault(); $btnSave.trigger('click'); }
      if (isTA && (ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') { ev.preventDefault(); $btnSave.trigger('click'); }
      if (ev.key === 'Escape') { ev.preventDefault(); this.cancelEdit($display); }
    });

    // buttons
    $btnSave.on('click', async () => {
      const newVal = $input.val();
      await this.save($display, newVal);
    });
    $btnCancel.on('click', () => this.cancelEdit($display));
  }

  async save($display, newVal) {
    const $wrap = $display.closest(this.wrapSelector);
    const ds = $wrap.data(); // {type, name, pk, model,...}

    // disable inputs
    $display.find('input, textarea, button').prop('disabled', true);

    try {
      this.register.register_changes(String(ds.pk), String(ds.name), String(newVal), String(this.oldValue));
      if (String(ds.pk) !== 'None') {
        $display.html(this.busy);
      } else {
        // immediate optimistic update if no PK
        if ((ds.type || 'text').toLowerCase() === 'text') {
          $display.text(newVal);
        } else {
          $display.html(this._br(newVal));
        }
      }
    } catch (err) {
      // show error via portal using the template node (if present) or a generic one
      const $errTemplate = $wrap.children('.widget-error').first();
      this._showPortal($wrap, $errTemplate.length ? $errTemplate : this._buildErrorNode('Save failed', this.oldValue));
    } finally {
      $wrap.removeClass('editing');
      this.$active = null;
    }
  }

  cancelEdit($display) {
    const html = $display.data('origHtml') || '';
    $display.html(html);
    $display.closest(this.wrapSelector).removeClass('editing');
    this.$active = null;
  }

  /* -------- Error portal helpers -------- */

  _buildErrorNode(message, original) {
    return $(
      `<div class="widget-error bg-danger text-white p-1 rounded shadow">
         ${message}
         <button class="btn btn-sm btn-outline-secondary revert-btn" data-original="${this._escapeAttr(original)}">Revert</button>
       </div>`
    );
  }

  _showPortal($wrap, $sourceError) {
    // remove any existing portal for this wrap
    this._removePortal($wrap);

    const rect = $wrap[0].getBoundingClientRect();
    const $portal = $('<div class="widget-error-portal"></div>')
      .css({
        position: 'fixed',
        zIndex: 2000,
        top: rect.top - 32,    // ~ -2em
        left: rect.left
      })
      .append($sourceError.clone(true).show());

    // bind the revert button to this wrap
    $portal.find('.revert-btn').each((_, btn) => {
      $(btn).attr('data-wrap', this._selectorFor($wrap));
    });

    $('body').append($portal);

    // keep it positioned on scroll/resize
    const reposition = () => {
      const r = $wrap[0].getBoundingClientRect();
      $portal.css({ top: r.top - 32, left: r.left });
    };
    $(window).on('scroll.widgetErrPos resize.widgetErrPos', reposition);
  }

  _removePortal($wrap) {
    $('.widget-error-portal').remove();
    $(window).off('.widgetErrPos');
    // ensure the in-DOM template remains hidden
    $wrap.children('.widget-error').hide();
  }

  /* -------- utils -------- */

  _getPlainText($el) {
    const html = ($el.html() || '').trim();
    if (!html) return '';
    const tmp = document.createElement('div');
    tmp.innerHTML = html.replace(/<br\s*\/?>/gi, '\n');
    return tmp.textContent || tmp.innerText || '';
  }

  _br(s) { return String(s).replace(/\n/g, '<br>'); }

  _escapeAttr(s) {
    return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // make a stable selector for data-wrap (uses an ID if present; otherwise adds one)
  _selectorFor($el) {
    let id = $el.attr('id');
    if (!id) {
      id = 'editable-' + Math.random().toString(36).slice(2, 9);
      $el.attr('id', id);
    }
    return '#' + id;
  }
}

