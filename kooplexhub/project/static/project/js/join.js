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

        $(document).on('click', 'button[data-bs-toggle="tab"]', this._fetch);
    }

    destroy() {
        $(document).off('click', 'button[data-bs-toggle="tab"]', this._fetch);
    }

    _fetch (e) {
        const btn = e.target;
        const group = btn.closest('.nav-tabs')?.id;
        const tabId = btn.id;
        if (tabId && tabId==='tab-join-project') {
          const payload = { request: 'get-joinable' };
          this.wss.send(JSON.stringify(payload));
        }
    }

    _callback(message) {
        if (message.response==='get-joinable') {
	    const cls=this;
            $("#joinProjectSelection").replaceWith(message.replace);
	    $("table[name=join-project] tbody tr").on('click', function () {
                const pk = $(this).data('id');
                cls.wss.send(JSON.stringify({
                    request: 'join',
                    pk
                }));
            });
        } 
    }
}

