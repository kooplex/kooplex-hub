// ---- Inline editor ----
class InlineEditor {
  constructor(register, opts = {}) {
    this.register = register;
    this.selector = opts.selector || '.editable';
    this.active = null;      // currently editing element
    this.oldValue = null;    // save currently edited elements original value
    this.busy = `<div class="spinner-border" role="status"><span class="visually-hidden">Saving...</span></div>`;
    this.init();
  }

  init() {
    document.addEventListener('click', (e) => {
      // If clicking on an editable not in editing mode, start editing
      const el = e.target.closest(this.selector);
      if (el && !el.classList.contains('editing')) {
        e.preventDefault();
        this.startEdit(el);
      }
    });
  }

  startEdit(el) {
    // guard: only one active editor
    if (this.active) this.cancelEdit(this.active);

    const type = (el.dataset.type || 'text').toLowerCase();
    const value = this._getPlainText(el);
    this.oldValue = value;
    el.classList.add('editing');

    // Create editor UI
    const wrapper = document.createElement('div');
    const input =
      type === 'textarea'
        ? document.createElement('textarea')
        : document.createElement('input');

    input.className = `form-control form-control-sm ${type === 'textarea' ? 'editable-textarea' : 'editable-input'}`;
    if (type !== 'textarea') input.type = 'text';
    input.value = value;

    const toolbar = document.createElement('div');
    toolbar.className = 'editable-toolbar';

    const btnSave = document.createElement('button');
    btnSave.type = 'button';
    btnSave.className = 'btn btn-success';
    const iconSave = document.createElement('i');
    iconSave.className = 'icon-white fas fa-thumbs-up';
    btnSave.appendChild(iconSave);

    const btnCancel = document.createElement('button');
    btnCancel.type = 'button';
    btnCancel.className = 'btn btn-danger';
    const iconCancel = document.createElement('i');
    iconCancel.className = 'icon-white fas fa-thumbs-down';
    btnCancel.appendChild(iconCancel);

    toolbar.appendChild(btnSave);
    toolbar.appendChild(btnCancel);

    // Replace el content with editor
    el._origHTML = el.innerHTML;
    el.innerHTML = '';
    el.appendChild(input);
    if (type === 'textarea') el.appendChild(toolbar);

    input.focus();
    if (type === 'text') input.select();

    // Keyboard shortcuts
    input.addEventListener('keydown', (ev) => {
      if (type === 'text') {
        if (ev.key === 'Enter') { ev.preventDefault(); btnSave.click(); }
      } else { // textarea
        if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') { ev.preventDefault(); btnSave.click(); }
      }
      if (ev.key === 'Escape') { ev.preventDefault(); this.cancelEdit(el); }
    });

    // Buttons
    btnSave.addEventListener('click', async () => {
      const newVal = input.value;
      await this.save(el, newVal);
    });
    btnCancel.addEventListener('click', () => this.cancelEdit(el));

    this.active = el;
  }

  async save(el, newVal) {
    // optimistic UI: disable inputs
    const inputs = el.querySelectorAll('input, textarea, button');
    inputs.forEach(i => i.disabled = true);

    try {
      this.register.register_changes(el.dataset.pk, el.dataset.name, newVal, this.oldValue);
      // Update UI with returned value (or the submitted one)
      if (el.dataset.pk !== "None") {
        el.innerHTML = this.busy;
      }
    } catch (err) {
      console.error(err);
      // Basic error hint (replace with your toast)
      el.innerHTML = `<span class="text-danger">Save failed</span>`;
    } finally {
      el.classList.remove('editing');
      this.active = null;
    }
  }

  cancelEdit(el) {
    el.innerHTML = el._origHTML || '';
    el.classList.remove('editing');
    this.active = null;
  }

  _getPlainText(el) {
    // Convert existing HTML (including <br>) to plain text
    const html = el.innerHTML.trim();
    if (!html) return '';
    const tmp = document.createElement('div');
    tmp.innerHTML = html.replace(/<br\s*\/?>/gi, '\n');
    return tmp.textContent || tmp.innerText || '';
  }

  _escapeHTML(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }
}

