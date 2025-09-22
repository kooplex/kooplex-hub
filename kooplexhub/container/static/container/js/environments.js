// refresh environment control
class FetchContainer {
    constructor(opts = {}) {
        this.userid = opts.userid || null;
        this.endpoint = opts.endpoint || null;

        this.wss = null;
        this._fetch = this._fetch.bind(this);
        this._autoadd = this._autoadd.bind(this);

        this.init();
    }

    init() {
        this.wss = new ManagedWebSocket(this.endpoint);
        $(document).on('shown.bs.tab', 'button[data-bs-toggle="tab"]', this._fetch);
        $(document).on('click', '[id^=environmentControl-][data-id][data-autoadd]', this._autoadd);
    }

    destroy() {
        $(document).off('shown.bs.tab', 'button[data-bs-toggle="tab"]', this._fetch);
        $(document).off('click', '[id^=environmentControl-][data-id][data-autoadd]', this._autoadd);
    }

    _fetch (e) {
        const btn = e.target;
        const group = btn.closest('.nav-tabs')?.id;
        const tabId = btn.id;

        // If it's an Environments tab, fire the data fetch
        if (tabId && tabId.startsWith('environments-tab-')) {
          const objectId = $(btn).data('id');
          const payload = { pk: objectId };
          this.wss.send(JSON.stringify(payload));
        }
    }

    _autoadd (e) {
        const btn = e.target;
        const objectId = $(btn).data('id');
        $(`#environmentControl-${objectId}`).replaceWith(`<div id="environmentControl-${objectId}" class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>`)

        var data = {
            pk: objectId,
            request: 'autoadd',
        }
      this.wss.send(JSON.stringify(data));
    }
}



