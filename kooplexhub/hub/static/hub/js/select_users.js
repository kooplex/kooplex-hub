// User Selection Modal Logic
class UserHandler {
    constructor(opts = {}) {
        this.pk = null;
        this.instance = null;
	this.changed = null;
        this.users = [];
        this.selectedUserIds = [];
        this.markedUserIds = [];

        this.usersDataSelector     = opts.usersDataSelector     || '#users_data';
        this.uploadInputSelector   = opts.uploadInputSelector   || '#user-upload';
        this.spinnerSelector       = opts.spinnerSelector       || '#user-upload-spinner';
        this.removeUserSelector    = opts.removeUserSelector    || '[name=remove][data-id][data-remove=user]';
        this.triggerSelector       = opts.triggerSelector       || '[name=users][data-editable=True]';
        this.wsEndpoint            = opts.wsEndpoint            || null;
        this.wss                   = null;    // ManagedWebSocket for parsing
        this.pendingRequests       = new Set(); // track request_ids while processing
    
        // bind
        this._onUploadChange = this._onUploadChange.bind(this);
        this._onWSMessage    = this._onWSMessage.bind(this);
        this._removeUserClick = this._removeUserClick.bind(this);
        this._triggerClick = this._triggerClick.bind(this);
        this.init();
    }

// ---- Initialization ----
    init() {
        this._initUsers();
        this._initTogglers();
        this._initSearch();
        this._initConfirmButton();
        this._initUpload();

        if (this.wsEndpoint) {
          this.wss = new ManagedWebSocket(this.wsEndpoint, { onMessage: this._onWSMessage });
        }
        $(document).on('click', this.removeUserSelector, this._removeUserClick);
        $(document).on('click', this.triggerSelector, this._triggerClick);
    }

    destroy() {
        $(document).off('click', this.removeUserSelector, this._removeUserClick);
        $(document).off('click', this.removeUserSelector, this._removeUserClick);
    }

    _triggerClick(event) {
        const $widget = $(event.currentTarget);
        const objectId = $widget.data('id') || 'None';
	    console.log(objectId)
        const kind = $widget.data('kind');
        this.openModal(objectId, kind);
    }

    _removeUserClick(event) {
        const $button = $(event.currentTarget);
        this.removeUser($button.data('id'));
    }

    _initUsers() {
        const usersData = JSON.parse(document.querySelector(this.usersDataSelector).textContent);

        usersData.forEach(userDict => {
            const pk = Object.keys(userDict)[0];
            const userDetails = userDict[pk];
            this.users.push({
                pk: parseInt(pk),
                name_and_username: userDetails.name_and_username,
                search: userDetails.search
            });
        });

        $('#user-search-results').hide();
    }

    _initSearch() {
        $('#search-user').on('input', () => {
            const query = $('#search-user').val().toLowerCase().trim().replaceAll(' ', '');
            if (query) {
                const matches = this.users
                    .filter(user =>
                        this.selectedUserIds.indexOf(user.pk) === -1 &&
                        user.search.includes(query)
                    )
                    .slice(0, 5);

                $('#user-search-results').empty().show();
                matches.forEach(user => {
                    $('#user-search-results').append(
                        `<li class="list-group-item list-group-item-action" data-pk="${user.pk}">
                            ${user.name_and_username}
                        </li>`
                    );
                });

                // Attach click handler for adding users
                $('#user-search-results li').off('click').on('click', (e) => {
                    const pk = $(e.currentTarget).data('pk');
                    this.addUser(pk);
                });
            } else {
                $('#user-search-results').hide();
            }
        });
    }

    _initTogglers() {
        $(document).on("change", "[data-toggle='toggle'][name=usermarker]", (e) => {
            const isChecked = $(e.currentTarget).prop("checked");
            const pk = $(e.currentTarget).data('id');
            if (isChecked) {
                this.markedUserIds.push(pk);
            } else {
                this.markedUserIds = this.markedUserIds.filter(value => value !== pk);
            }
            this.changed = true;
        });
    }

    _initConfirmButton() {
        $('#confirm-users-selection').on('click', () => {
            if (!this.pk) return;
            if (this.changed) {
              this._saveChanges();
	    } else {
              this._toast('Userlist is unchanged');
	    }

            $('.users-modal').modal('hide');
            this.pk = null;
        });
    }

    _saveChanges() {
      const request_id = this._uuid();
      this._setUploadBusy(true);
      if (!this.wss || typeof this.wss.send !== 'function') {
        this._setUploadBusy(false);
        this._toast('Save userlist channel is not available.');
        return;
      }
	    if (this.pk === 'None') {

console.error("NOT IMPLEMENTED")
		    return
	    }
      // Track request so we only react to our own response
      this.pendingRequests.add(request_id);
      // Send to server new userlist to save
      this.wss.send(JSON.stringify({
        request: 'save-users',
        request_id,
        pk: this.pk,
	ids: this.selectedUserIds,
	marked_ids: this.markedUserIds
      }));
    }

    _initUpload() {
      const $input = $(this.uploadInputSelector);
      if (!$input.length) return;
      $input.on('change', this._onUploadChange);
    }
  
    async _onUploadChange(e) {
      const file = e.currentTarget.files && e.currentTarget.files[0];
      if (!file) return;
  
      // Only plaintext allowed
      if (!(file.type === 'text/plain' || /\.txt$/i.test(file.name))) {
        this._toast('Please upload a plain text file (.txt).');
        e.currentTarget.value = '';
        return;
      }
  
      const text = await file.text(); // modern browsers
      const request_id = this._uuid();
  
      this._setUploadBusy(true);
  
      if (!this.wss || typeof this.wss.send !== 'function') {
        this._setUploadBusy(false);
        this._toast('Upload channel is not available.');
        e.currentTarget.value = '';
        return;
      }
  
      // Track request so we only react to our own response
      this.pendingRequests.add(request_id);
  
      // Send to server for parsing
      this.wss.send(JSON.stringify({
        request: 'parse-users-from-file',
        request_id,
        pk: this.pk,
        filename: file.name,
        content: text
      }));
  
      // clear input so same file can be selected again if needed
      e.currentTarget.value = '';
    }
  
    _onWSMessage(message) {
      // Normalize WS payload
      let data = message;
      if (data && typeof data === 'object' && 'data' in data) {
        try { data = JSON.parse(data.data); } catch { /* ignore */ }
      } else if (typeof data === 'string') {
        try { data = JSON.parse(data); } catch { /* ignore */ }
      }
  
      if (!data || data.request_id && !this.pendingRequests.has(data.request_id)) {
        // Not our response
        return;
      }
  
      // Stop spinner for our request
      if (data.request_id) this.pendingRequests.delete(data.request_id);
      if (this.pendingRequests.size === 0) this._setUploadBusy(false);
  
      if (data.error) {
        this._toast(`Parse error: ${data.error}`);
        return;
      }

      if (data.response==='parse-users-from-file') {
        this._parsed_users(data);
      } else if (data.response==='get-users') {
        this._set_users(data);
      } else if (data.response==='save-users') {
	$(`[name="users"][data-id="${data.pk}"]`).replaceWith(data.refresh);
      }

  
    }

    _parsed_users(data) {
      // Expecting { response: 'parsed-users', ids: [..] }
      const ids = Array.isArray(data.ids) ? data.ids : [];
      let added = 0;
      ids.forEach(id => {
        if (!this.selectedUserIds.includes(id)) {
          this.addUser(id);
          added++;
        }
      });
      if (added === 0) {
        this._toast('No new users found in the file.');
      } else {
        this._toast(`Added ${added} user${added === 1 ? '' : 's'} from file.`);
      }
    }
  
    _set_users(data) {
      // Expecting { response: 'get-users', pk:, ids: [..], marked_ids: [..] }
      const ids = Array.isArray(data.ids) ? data.ids : [];
      const marked_ids = Array.isArray(data.marked_ids) ? data.marked_ids : [];
      const objectId = data.pk ? data.pk : null;
      const $dataEl = $(`[name="users"][data-id="${objectId}"]`);
      this.selectedUserIds = ids.slice();
      this.markedUserIds = marked_ids.slice();
      this.changed = false;

      $('tr[data-id]').each((_, el) => {
          const pk = $(el).data('id');
	  const selected = this.selectedUserIds.includes(pk);
	  const marked = this.markedUserIds.includes(pk);
          $(el).toggle(selected);
          const toggleButton = $(el).find(`input[name=usermarker][data-id=${pk}]`);
          if (selected && marked) {
            toggleButton.bootstrapToggle('on');
          } else {
            toggleButton.bootstrapToggle('off');
          }
      });
      this._toast('Userlist refreshed');
    }

    _setUploadBusy(isBusy) {
      $(this.spinnerSelector).toggleClass('d-none', !isBusy);
      const $input = $(this.uploadInputSelector);
      $input.prop('disabled', isBusy);
      // Optionally disable the confirm while busy:
      $('#confirm-users-selection').prop('disabled', isBusy);
    }
  
    _toast(msg) {
      // Replace with your own toaster if you have one
      feedback(msg);
    }
  
    _uuid() {
      // Simple request id (good enough for correlating)
      return 'req_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    }


    openModal(objectId, kind) {
      this.pk = objectId === "None" ? "None" : parseInt(objectId);
      this.instance = $(".users-modal").data('instance');
      const request_id = this._uuid();
      this._setUploadBusy(true);
  
      if (!this.wss || typeof this.wss.send !== 'function') {
        this._setUploadBusy(false);
        this._toast('Refresh userlist channel is not available.');
        return;
      }
  
      // Track request so we only react to our own response
      this.pendingRequests.add(request_id);
  
      // Send to server userlist request
      this.wss.send(JSON.stringify({
        request: 'get-users',
        request_id,
        pk: this.pk
      }));

      $(".users-modal").modal('show');
    }

    addUser(pk) {
        this.selectedUserIds.push(pk);
        const is_marked = $(`input[data-id=${pk}]`).prop('checked');
        if (is_marked) {
            this.markedUserIds.push(pk);
        } else {
            this.markedUserIds = this.markedUserIds.filter(value => value !== pk);
        }

        $(`tr[data-id=${pk}]`).show();
        $('#search-user').val('');
        $('#user-search-results').hide();
        this.changed = true;
    }

    removeUser(pk) {
        $(`tr[data-id=${pk}]`).hide();
        this.selectedUserIds = this.selectedUserIds.filter(value => value !== pk);
        this.changed = true;
    }
}

