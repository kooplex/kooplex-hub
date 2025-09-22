///////////////////////////////////////
// Container Control button Logic

class ContainerControl {
  constructor(opts = {}) {
    this.userid = opts.userid || null;
    this.endpoint = opts.endpoint || null;
    this.buttonSelector = opts.buttonSelector || 'button[data-pk][data-action]';
    this.openSelector = opts.openSelector || 'button[name="opencontainer"][data-url]';
    this.busy = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;

    this._onButtonClick = this._onButtonClick.bind(this);
    this._onOpenButtonClick = this._onOpenButtonClick.bind(this);

    this.init();
  }

  init() {
    if (this.endpoint) {
      this.wss = new ManagedWebSocket(this.endpoint);
    } else {
      console.error('Option endpoint is not set');
    }

    // Delegate the event to the document for dynamic elements
    $(document).on('click', this.buttonSelector, this._onButtonClick);
    $(document).on('click', this.openSelector, this._onOpenButtonClick);
  }

  destroy() {
    $(document).off('click', this.buttonSelector, this._onButtonClick);
    $(document).off('click', this.openSelector, this._onOpenButtonClick);
  }

  _onButtonClick(event) {
    const $button = $(event.currentTarget);
    const pk = $button.data('pk');
    const action = $button.data('action');
    this._send(pk, action);
    this._setBusyState($button);
  }

  _send(pk, action) {
    this.wss.send(JSON.stringify({
      pk,
      userid: this.userid,
      request: action
    }));
  }

  _setBusyState($button) {
    const originalContent = $button.html();
    $button.html(`${this.busy} ${$button.text()}`);
    $button.prop('disabled', true);

    setTimeout(() => {
      $button.html(originalContent);
      $button.prop('disabled', false);
    }, 3000);
  }

  _onOpenButtonClick(event) {
    const $button = $(event.currentTarget);
    const url = $button.data('url'); // Get the URL from the button's data-url attribute
    console.log("Opening: " + url);

    var win = window.open(url, '_blank');
    if (win) {
      win.focus();
    }
  }
}


//   // Attach Save Changes Event
//   $(document).on('click', '[name=save][data-id][data-instance=container]', function() {
//       wss_containerconfig.createnew();
//   })
//   
//   
//   // handle teleport button
//   $(document).on('click', '[data-field=start_teleport][name][data-id]', function() {
//       let pk=$(this).data('id')
//       let name=$(this).attr('name')
//       let widgetId = `container-teleport-${pk}`
//       containerId = pk === "None" ? "None" : parseInt(pk)
//       applyButton(widgetId, name==='grant'?'revoke':'grant')
//       wss_containerconfig.register_changes(containerId, 'start_teleport', name, $(widgetId).data('orig'))
//   })
//   
//   
//   // handle seafile button
//   $(document).on('click', '[data-field=start_seafile][name][data-id]', function() {
//       let pk=$(this).data('id')
//       let name=$(this).attr('name')
//       let widgetId = `container-seafile-${pk}`
//       containerId = pk === "None" ? "None" : parseInt(pk)
//       applyButton(widgetId, name==='grant'?'revoke':'grant')
//       wss_containerconfig.register_changes(containerId, 'start_seafile', name, $(widgetId).data('orig'))
//   })
//   
