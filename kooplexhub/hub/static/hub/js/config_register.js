// config_register.js
//
function getMethodAndContext(path, root = window) {
  const parts = path.split('.');
  const methodName = parts.pop();
  const ctx = parts.reduce((acc, key) => acc?.[key], root);
  const fn = ctx?.[methodName];
  return { fn, ctx };
}

class ConfigHandler {
    constructor(opts = {}) {
        this.endpoint = opts.endpoint || null;
        this.userid = opts.userid || null;
        this.request = opts.request || 'config';
        this.model = opts.model || '';
        this.pk_mapping = opts.pk_mapping || 'pk';
        this.required = opts.required || [];
        this.dummy = opts.pk_new || 'None';
        this.sendDelay = opts.sendDelay || 300;
        this.changeBuffer = new Map();        // Internal change buffer
        this.newObject = {};
        this.sendTimer = null;                // Timer to throttle sends
        this.handleCallback = this.handleCallback.bind(this); // <- bind once
        this.pendingRequests = new Set(); // track request_ids while processing
        if (this.endpoint) {
            this.wss = new ManagedWebSocket(this.endpoint, {
                onMessage: this.handleCallback,
            });
	} else {
            throw new Error('No endpoint is provided. Cannot send changes to server.');
        }
    }

    // Check equality of two arrays
    arraysEqual(arr1, arr2) {
        // Check if the arrays have the same length
        if (arr1.length !== arr2.length) {
            return false
        }
        // Sort both arrays and compare them element by element
        var sortedArr1 = arr1.slice().sort((a, b) => a - b) // Sort a copy of arr1
        var sortedArr2 = arr2.slice().sort((a, b) => a - b) // Sort a copy of arr2
        // Check if all elements are equal
        for (var i = 0; i < sortedArr1.length; i++) {
            if (sortedArr1[i] !== sortedArr2[i]) {
                return false
            }
        }
        // If all checks passed, the arrays are equal
        return true
    }

    // Check if pk references new instance config
    isnew(pk) {
        return (pk === null || pk === undefined || pk === "" || pk === "None" || (typeof pk === "number" && isNaN(pk)));
    }

    _uuid() {
      // Simple request id (good enough for correlating)
      return 'req_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    }


    // Send record to server via ws
    flushChanges(pk) {
        const entry = this.changeBuffer.get(pk);
        if (!entry || !entry.changes || Object.keys(entry.changes).length === 0) return;
        this.wss.send(JSON.stringify(entry));
        console.log("Dequeued changes:", entry);
        this.changeBuffer.delete(pk); // Clean up // FIXME: only on respoonse!
    }

    // Keep track of changes entered in UI
    register_changes(pk, fieldName, newValue, oldValue) {
        if (this.isnew(pk)) {
            this.newObject[fieldName]=newValue;
            this.showSaveChanges();
            this.wss.send(JSON.stringify({
                request: 'update-widget',
                field: fieldName,
                value: newValue,
	    }));
	} else {
            const request_id = this._uuid();
            this.pendingRequests.add(request_id);
            let entry = this.changeBuffer.get(pk);
            if (!entry) {
                entry = { userid: this.userid, pk: pk, request_id, request: this.request, changes: {}, timer: null };
                this.changeBuffer.set(pk, entry);
            }
            var changed = $.isArray(newValue) ? ! this.arraysEqual(newValue, oldValue) : oldValue !== newValue;
            if (! changed) {
                return false;
            }
            entry.changes[fieldName] = newValue;
            if (entry.timer) {
                clearTimeout(entry.timer);
            }
            entry.timer = setTimeout(() => this.flushChanges(pk), this.sendDelay);
	}
	return true;
    }

    // Helper to request saving new instance
    createnew() {
        this.newObject["request"] = `create-${this.model}`;
        this.wss.send(JSON.stringify(this.newObject));
        console.log("Sent as new:", this.newObject);
    }

    // Show Save Changes button
    showSaveChanges() {
        if (Object.keys(this.newObject).length == 0) {
            return;
	}
        const hasAllKeys = this.required.every(key => Object.prototype.hasOwnProperty.call(this.newObject, key));
        if (this.required.length > 0 && ! hasAllKeys) {
            return;
	}
        let widget=$(`[name=save][data-id=${this.dummy}][data-instance=${this.model}]`);
        this.createnew = this.createnew.bind(this);
        $(document).on('click', widget, this.createnew);
	    console.log(widget)
        widget.removeClass("d-none");
        widget.removeAttr("disabled");
    }

    // handle web socket callback
    handleCallback(message) {
        $(`[data-model=${message.model}][data-pk="${message.pk}"][data-name=${message.attr}]`).replaceWith(message.widget);
    }

}

