(function () {
   var courseid;
   const activeEditors = new Map();

   function makeKey(student, assignment) {
     return `${student}::${assignment}`;
   }

  // Build HTML for a given trigger element
  function popoverContent(triggerEl) {
    if (triggerEl._popHTML) return triggerEl._popHTML;
    const tpl = document.getElementById('score-popover-template');
    const frag = tpl.content.cloneNode(true);
    courseid = $(tpl).data('id');

    // Prefill from the cell
    const text = triggerEl.textContent.trim();
    const score = isNaN(+text) ? '' : +text;
    const scoreInput = frag.querySelector('.js-score');
    scoreInput.value = score;
    scoreInput.setAttribute('value', score);

    const commentInput = frag.querySelector('.js-comment');
    commentInput.value = '';
    commentInput.setAttribute('placeholder', 'loading...');

    const wrapper = document.createElement('div');
    wrapper.appendChild(frag);
    // store built HTML on the trigger
    triggerEl._popHTML = wrapper.innerHTML;
    return triggerEl._popHTML;
  }

  // Initialize popovers inside a modal (idempotent)
  function initPopovers(modal) {
    modal.querySelectorAll('.score-popover').forEach(function (el) {
      if (el._popInit) return;
      el._popInit = true;
      new bootstrap.Popover(el, {
        html: true,
        container: modal,          // stay inside modal
        boundary: modal,           // prevent overflow
        placement: 'auto',
        sanitize: false,           // our HTML
        content: () => popoverContent(el),
        trigger: 'manual'
      });
    });
  }

  // When any modal opens, wire up popovers inside
  document.addEventListener('shown.bs.modal', function (e) {
    const modal = e.target;
    initPopovers(modal);
  });

  // Show on cell click; hide others first
  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('.score-popover');
    if (!trigger) return;

    const modal = trigger.closest('.modal');
    // Hide any open popovers in this modal
    modal.querySelectorAll('.score-popover[aria-describedby]').forEach(function (t) {
      bootstrap.Popover.getInstance(t)?.hide();
    });

    bootstrap.Popover.getInstance(trigger).show();

    // After show, get the live popover element and register it
    const id = trigger.getAttribute('aria-describedby');
    const popEl = id && document.getElementById(id);
    if (popEl) {
      const key = makeKey(trigger.dataset.student, trigger.dataset.assignment);
      activeEditors.set(key, popEl);

      // ensure placeholder is visible while loading
      const input = popEl.querySelector('.js-comment');
      if (input) {
        input.value = '';
        input.setAttribute('placeholder', 'loading...');
      }

      // fire the fetch
      setTimeout(function () {
        const payload = {
          request: 'fetch',
          courseid: courseid,
          student: trigger.dataset.student,
          assignment: trigger.dataset.assignment,
        };
        wss_score.send(JSON.stringify(payload));
      }, 10);

      // clean registry on hide
      trigger.addEventListener('hidden.bs.popover', function onHide() {
        activeEditors.delete(key);
        trigger.removeEventListener('hidden.bs.popover', onHide);
      });
    }
  });

	
function receiveComment(message) {
	console.log(message);
    if (message.student && message.assignment) {
	    console.log(activeEditors)
        const key = makeKey(message.student, message.assignment);
	    console.log(key)
        const popEl = activeEditors.get(key);
        if (popEl) {
            const input = popEl.querySelector('.js-comment');
            if (input) {
		    console.log('IN')
		const comment = message.comment || '';
                input.value = comment;
                input.setAttribute('placeholder', '');
                input.setAttribute('value', comment);
            }
        }
    }
}

$(document).ready(function() {
  if (wsURLs.assignment_score) {
      wss_score = new ManagedWebSocket(wsURLs.assignment_score, {
          onMessage: receiveComment,
      });
  }
});

// Delegated handlers for buttons inside any Bootstrap popover
$(document).on('click', '.popover .js-cancel', function () {
  const popEl = this.closest('.popover');
  if (!popEl) return;
  const id = popEl.id; // popover id assigned by Bootstrap
  const trigger = document.querySelector('.score-popover[aria-describedby="' + id + '"]');
  if (trigger) {
    bootstrap.Popover.getInstance(trigger)?.hide();
  }
});

$(document).on('click', '.popover .js-save', function () {
  const popEl = this.closest('.popover');
  if (!popEl) return;
  const id = popEl.id;
  const trigger = document.querySelector('.score-popover[aria-describedby="' + id + '"]');
  if (!trigger) return;

  // Read current values from the live popover DOM
  const scoreInput   = popEl.querySelector('.js-score');
  const commentInput = popEl.querySelector('.js-comment');
  const score   = scoreInput ? scoreInput.value : '';
  const comment = commentInput ? commentInput.value : '';

  // Update the cell text immediately
  trigger.textContent = score === '' ? '—' : String(score);

  const payload = {
    request: 'store',
    student:   trigger.dataset.student,
    assignment: trigger.dataset.assignment,
    courseid, score, comment
  };
  console.log(payload);
  wss_score.send(JSON.stringify(payload));

  // Hide the popover
  trigger._popHTML = null;
  bootstrap.Popover.getInstance(trigger)?.hide();
});



  // Close if clicking elsewhere in the modal
  document.addEventListener('click', function (e) {
    if (e.target.closest('.score-popover') || e.target.closest('.popover')) return;
    document.querySelectorAll('.score-popover[aria-describedby]').forEach(function (t) {
      bootstrap.Popover.getInstance(t)?.hide();
    });
  });
})();



