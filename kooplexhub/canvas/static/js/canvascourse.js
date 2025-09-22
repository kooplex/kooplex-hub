// static/js/canvascourse.js
class FetchCanvasCourses {
    constructor(register, opts = {}) {
        this.register = register || null;
        this.userid = opts.userid || null;
        this.endpoint = opts.endpoint || null;
        this.triggerSelector = opts.triggerSelector || '[id=newCourseModal]';

        this.wss = null;
        this._fetch = this._fetch.bind(this);
        this._callback = this._callback.bind(this);

        this.init();
    }

    init() {
        this.wss = new ManagedWebSocket(this.endpoint, {
            onMessage: this._callback,
	});
        $(document).on('shown.bs.modal', this.triggerSelector, this._fetch);
    }

    destroy() {
        $(document).off('shown.bs.modal', this.triggerSelector, this._fetch);
    }

    _fetch(event) {
        this.wss.send(JSON.stringify({
	  userid: this.userid,
          request: 'get-courses',
        }));
    }

    _callback(message) {
        if (message.response==='get-courses') {
            $("table[name=canvas-course] tbody tr").on('click', function () {
                const pk = $(this).data('id');
                const canvas_name = $(this).data('tail');
                $("[data-id=None][data-field=name][data-instance=course]").editable('setValue', canvas_name, true)
                $("[data-id=None][data-field=description][data-instance=course]").editable('setValue', canvas_name + " imported from canvas", true)
            	this.register.register_changes('None', 'name', canvas_name, '')
            	this.register.register_changes('None', 'description', canvas_name + " imported from canvas", '')
            	this.register.register_changes('None', 'canvasid', pk, '')
            });
        }
    }
}

