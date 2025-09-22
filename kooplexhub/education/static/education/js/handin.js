class AssignmentHandin {
    constructor(opts = {}) {
        this.userid = opts.userid || null;
        this.endpoint = opts.endpoint || null;
        this.handinSelector = opts.handinSelector || '[type=submit][data-submit=handin][data-id]';
        this.wss = null;
        this._submit = this._submit.bind(this);

        this.init();
    }

    init() {
        this.wss = new ManagedWebSocket(this.endpoint);
        $(document).on('click', this.handinSelector, this._submit);
    }

    destroy() {
        $(document).off('click', this.handinSelector, this._submit);
    }

    _submit (event) {
        const $button = $(event.target);
        const pk=$button.data('id');
        this.wss.send(JSON.stringify({ pk, userid: this.userid }));
	$button.attr('disabled', true);
    }
}



