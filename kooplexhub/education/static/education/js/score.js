// score.js — class-based refactor (drop-in replacement)
class ScoreHandler {
  constructor(opts = {}) {
    // state
    this.endpoint = opts.endpoint || null;
    this.courseid = null;
    this.activeEditors = new Map();
    this.socket = null; // ManagedWebSocket instance

    // method bindings
    this.initPopovers = this.initPopovers.bind(this);
    this._buildPopoverContent = this._buildPopoverContent.bind(this);
    this._onCellClick = this._onCellClick.bind(this);
    this._onOutsideClick = this._onOutsideClick.bind(this);
    this._onCancelClick = this._onCancelClick.bind(this);
    this._onSaveClick = this._onSaveClick.bind(this);
    this._receiveComment = this._receiveComment.bind(this);

    // listeners
    document.addEventListener('click', this._onCellClick);
    document.addEventListener('click', this._onOutsideClick);

    // delegated handlers inside bootstrap popovers
    $(document).on('click', '.popover .js-cancel', this._onCancelClick);
    $(document).on('click', '.popover .js-save', this._onSaveClick);

    // setup websocket after DOM ready (keeps original timing/behavior)
    $(document).ready(() => this._setupWebSocket());
  }

  // ---------- utils ----------
  _makeKey(student, assignment) {
    return `${student}::${assignment}`;
  }

  // Build HTML for a given trigger element (cached on element)
  _buildPopoverContent(triggerEl) {
    if (triggerEl._popHTML) return triggerEl._popHTML;

    const tpl = document.getElementById('score-popover-template');
    const frag = tpl.content.cloneNode(true);
    // pick up course id from template (as in original)
    this.courseid = $(tpl).data('id');

    // Prefill from the cell
    const text = (triggerEl.textContent || '').trim();
    const score = isNaN(+text) ? '' : +text;

    const scoreInput = frag.querySelector('.js-score');
    if (scoreInput) {
      scoreInput.value = score;
      scoreInput.setAttribute('value', score);
    }

    const commentInput = frag.querySelector('.js-comment');
    if (commentInput) {
      commentInput.value = '';
      commentInput.setAttribute('placeholder', 'loading...');
    }

    const wrapper = document.createElement('div');
    wrapper.appendChild(frag);
    triggerEl._popHTML = wrapper.innerHTML; // cache
    return triggerEl._popHTML;
  }

  // ---------- public API ----------
  // Initialize popovers inside a modal (idempotent)
  initPopovers(modal) {
    modal.querySelectorAll('.score-popover').forEach((el) => {
      if (el._popInit) return;
      el._popInit = true;

      new bootstrap.Popover(el, {
        html: true,
        container: modal,     // stay inside modal
        boundary: modal,      // prevent overflow
        placement: 'auto',
        sanitize: false,      // we control HTML
        content: () => this._buildPopoverContent(el),
        trigger: 'manual',
      });
    });
  }

  // ---------- event handlers ----------
  _onCellClick(e) {
    const trigger = e.target.closest('.score-popover');
    if (!trigger) return;

    const modal = trigger.closest('.modal');
    if (!modal) return;

    // hide any open popovers in this modal
    modal
      .querySelectorAll('.score-popover[aria-describedby]')
      .forEach((t) => {
        bootstrap.Popover.getInstance(t)?.hide();
      });

    // show the clicked one
    bootstrap.Popover.getInstance(trigger).show();

    // After show, get the live popover element and register it
    const id = trigger.getAttribute('aria-describedby');
    const popEl = id && document.getElementById(id);
    if (!popEl) return;

    const key = this._makeKey(trigger.dataset.student, trigger.dataset.assignment);
    this.activeEditors.set(key, popEl);

    // ensure placeholder is visible while loading
    const input = popEl.querySelector('.js-comment');
    if (input) {
      input.value = '';
      input.setAttribute('placeholder', 'loading...');
    }

    // fire the fetch slightly later (preserves original timing)
    setTimeout(() => {
      const payload = {
        request: 'fetch',
        courseid: this.courseid,
        student: trigger.dataset.student,
        assignment: trigger.dataset.assignment,
      };
      if (this.socket) this.socket.send(JSON.stringify(payload));
    }, 10);

    // clean registry on hide
    const onHide = () => {
      this.activeEditors.delete(key);
      trigger.removeEventListener('hidden.bs.popover', onHide);
    };
    trigger.addEventListener('hidden.bs.popover', onHide);
  }

  _onOutsideClick(e) {
    // Close if clicking elsewhere in the modal, ignore clicks on triggers and popovers
    if (e.target.closest('.score-popover') || e.target.closest('.popover')) return;

    document
      .querySelectorAll('.score-popover[aria-describedby]')
      .forEach((t) => {
        bootstrap.Popover.getInstance(t)?.hide();
      });
  }

  _onCancelClick() {
    const popEl = this.closest && this.closest('.popover');
    if (!popEl) return;
    const id = popEl.id;
    const trigger = document.querySelector(
      '.score-popover[aria-describedby="' + id + '"]'
    );
    if (trigger) {
      bootstrap.Popover.getInstance(trigger)?.hide();
    }
  }

  _onSaveClick(event) {
    const $button = $(event.currentTarget)[0];
    const popEl = $button.closest && $button.closest('.popover');
    if (!popEl) return;

    const id = popEl.id;
    const trigger = document.querySelector(
      '.score-popover[aria-describedby="' + id + '"]'
    );
    if (!trigger) return;

    // Read current values from the live popover DOM
    const scoreInput = popEl.querySelector('.js-score');
    const commentInput = popEl.querySelector('.js-comment');
    const score = scoreInput ? scoreInput.value : '';
    const comment = commentInput ? commentInput.value : '';

    // Update the cell text immediately
    trigger.textContent = score === '' ? '—' : String(score);

    const payload = {
      request: 'store',
      student: trigger.dataset.student,
      assignment: trigger.dataset.assignment,
      courseid: this.courseid,
      score,
      comment,
    };

    if (this.socket) this.socket.send(JSON.stringify(payload));

    // Hide the popover and clear cached HTML
    trigger._popHTML = null;
    bootstrap.Popover.getInstance(trigger)?.hide();
  }

  // ---------- websocket ----------
  _setupWebSocket() {
    // keep globals for compatibility with existing code
    if (this.endpoint) {
      this.socket = new ManagedWebSocket(this.endpoint, {
        onMessage: this._receiveComment,
      });
    }
  }

  _receiveComment(message) {
    // message: {student, assignment, comment}
    if (message && message.student && message.assignment) {
      const key = this._makeKey(message.student, message.assignment);
      const popEl = this.activeEditors.get(key);
      if (popEl) {
        const input = popEl.querySelector('.js-comment');
        if (input) {
          const comment = message.comment || '';
          input.value = comment;
          input.setAttribute('placeholder', '');
          input.setAttribute('value', comment);
        }
      }
    }
  }
}


