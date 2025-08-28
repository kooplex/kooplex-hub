// User Selection Modal Logic
class UserHandler {
    constructor(opts = {}) {
        this.pk = null;
        this.instance = null;
        this.selectedUserIds = [];
        this.originalUserIds = [];
        this.markedUserIds = [];
        this.originalMarkedIds = [];
        this.users = [];

        this.usersDataSelector     = opts.usersDataSelector     || '#users_data';
        this.uploadInputSelector   = opts.uploadInputSelector   || '#user-upload';
        this.spinnerSelector       = opts.spinnerSelector       || '#user-upload-spinner';
        this.wsEndpoint            = opts.wsEndpoint            || (wsURLs && wsURLs.handle_users) || null;
        this.wss                   = null;    // ManagedWebSocket for parsing
        this.pendingRequests       = new Set(); // track request_ids while processing
    
        // bind
        this._onUploadChange = this._onUploadChange.bind(this);
        this._onWSMessage    = this._onWSMessage.bind(this);
    }

    init() {
        this._initUsers();
        this._initTogglers();
        this._initSearch();
        this._initConfirmButton();
        this._initUpload();

        if (this.wsEndpoint) {
          this.wss = new ManagedWebSocket(this.wsEndpoint, { onMessage: this._onWSMessage });
        }
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
        });
    }

    _initConfirmButton() {
        $('#confirm-users-selection').on('click', () => {
            if (!this.pk) return;

            const cb    = this._resolveFn(this.register); // bound if it's a method path

            if (typeof cb === 'function') {
                let changed = cb(this.pk, 'marked', this.markedUserIds, this.originalMarkedIds);
                if (changed) {
                    cb(this.pk, 'users', this.selectedUserIds, []);
                } else {
                    cb(this.pk, 'users', this.selectedUserIds, this.originalUserIds);
                }
            } else {
              console.warn('UserHandler: no save function (register_changes) found.');
            }

            $('.users-modal').modal('hide');
            this.pk = null;
        });
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


    openModal(objectId, kind, callback) {
        this.pk = objectId === "None" ? "None" : parseInt(objectId);
        this.instance = $(".users-modal").data('instance');
        this.register = callback;

        const $dataEl = $(`[name="users"][data-id="${objectId}"][data-kind="${kind}"]`);
        this.selectedUserIds = $dataEl.data('users').slice();
        this.originalUserIds = $dataEl.data('users');
        this.markedUserIds = $dataEl.data('marked').slice();
        this.originalMarkedIds = $dataEl.data('marked');

        $('tr[data-id]').each((_, el) => {
            const pk = $(el).data('id');

            $(el).toggle(this.selectedUserIds.includes(pk));

            const toggleButton = $(el).find(`input[name=usermarker][data-id=${pk}]`);
            if (this.markedUserIds.includes(pk)) {
                toggleButton.bootstrapToggle('on');
            } else {
                toggleButton.bootstrapToggle('off');
            }
        });

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
    }

    removeUser(pk) {
        $(`tr[data-id=${pk}]`).hide();
        this.selectedUserIds = this.selectedUserIds.filter(value => value !== pk);
    }
}

// ---- Initialization ----
$(document).ready(function() {
	console.log(wsURLs)
    const userHandler = new UserHandler();
    userHandler.init();
    
    $(document).on('click', '[name=remove][data-id][data-remove=user]', function () {
        userHandler.removeUser($(this).data('id'));
    });

    $(document).on('click', '[name=users]', function() {
        const objectId = $(this).data('id');  // Get the id from the button's data-id attribute
        const kind = $(this).data('kind');
        const cb = $(this).data('callback');
        userHandler.openModal(objectId, kind, cb);
    });
});

