// join a project logic
class FetchJoinableProjects {
    constructor(opts = {}) {
        this.userid = opts.userid || null;
        this.endpoint = opts.endpoint || null;
        this._callback = this._callback.bind(this);

        this.wss = null;
        this._fetch = this._fetch.bind(this);

        this.init();
    }

    init() {
        this.wss = new ManagedWebSocket(this.endpoint, {
          onMessage: this._callback,
        });

        $(document).on('shown.bs.modal', 'button[data-bs-toggle="tab"]', this._fetch);
    }

    destroy() {
        $(document).off('shown.bs.modal', 'button[data-bs-toggle="tab"]', this._fetch);
    }

    _fetch (e) {
        const btn = e.target;
        const group = btn.closest('.nav-tabs')?.id;
        const tabId = btn.id;

        // If it's an Environments tab, fire the data fetch
        if (tabId && tabId.startsWith('environments-tab-')) {
          const objectId = $(btn).data('id');
          const payload = { request: 'get-joinable' };
          this.wss.send(JSON.stringify(payload));
        }
    }

    _callback(message) {
        if (message.response==='get-joinable') {
            $("#joinProjectSelection").replaceWith(data.replace);
	    $("table[name=join-project] tbody tr").on('click', function () {
                const pk = $(this).data('id');
                this.wss.send(JSON.stringify({
                    request: 'join',
                    pk
                }));
            });
        } 
    }
}

