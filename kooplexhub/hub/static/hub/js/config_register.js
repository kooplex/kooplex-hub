// config_register.js
//
function getMethodAndContext(path, root = window) {
  const parts = path.split('.');
  const methodName = parts.pop();
  const ctx = parts.reduce((acc, key) => acc?.[key], root);
  const fn = ctx?.[methodName];
  return { fn, ctx };
}

//
//
//
class ConfigHandler {
    constructor(endpoint, request, widget = null, instancetype = null, attribute = null, required = [], dummy = "None", sendDelay = 300) {
        this.widget = widget;
        this.instancetype = instancetype;
        this.attribute = attribute;
        this.required = required;
        this.dummy = dummy;
        this.request = request;
        this.sendDelay = sendDelay;
        // Internal change buffer
        this.changeBuffer = new Map();
        // Timer to throttle sends
        this.sendTimer = null;
        this.handleCallback = this.handleCallback.bind(this); // <- bind once
        this.wss = new ManagedWebSocket(endpoint, {
            onMessage: this.handleCallback,
        });
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
        return (pk === null || pk === undefined || pk === "" || (typeof pk === "number" && isNaN(pk)));
    }


    // Send record to server via ws
    flushChanges(pk) {
        const entry = this.changeBuffer.get(pk);
        if (!entry || !entry.changes || Object.keys(entry.changes).length === 0) return;
        this.wss.send(JSON.stringify(entry));
        console.log("Dequeued changes:", entry);
        this.changeBuffer.delete(pk); // Clean up
    }

    // Keep track of changes entered in UI
    register_changes(pk, fieldName, newValue, oldValue) {
        pk = this.isnew(pk) ? this.dummy : pk;
        let entry = this.changeBuffer.get(pk);

        if (!entry) {
            entry = { pk: pk, request: this.request, changes: {}, timer: null };
            this.changeBuffer.set(pk, entry);
        }

        var changed = $.isArray(newValue) ? ! this.arraysEqual(newValue, oldValue) : oldValue !== newValue;
        if (! changed) {
            return false;
        }

        // Store the change
        entry.changes[fieldName] = newValue;

        // Reset debounce timer
        if (entry.timer) {
            clearTimeout(entry.timer);
        }

        if (pk === this.dummy) {
            this.showSaveChanges();
	} else {
	    // only deque automatically if instance already exists
            entry.timer = setTimeout(() => this.flushChanges(pk), this.sendDelay);
        }
	return true;
    }

    // Helper to request saving new instance
    createnew() {
        this.flushChanges(this.dummy);
    }

    // Show Save Changes button
    showSaveChanges() {
        let entry = this.changeBuffer.get(this.dummy);
        if (! entry) {
            return;
	}
        const hasAllKeys = this.required.every(key => Object.prototype.hasOwnProperty.call(entry.changes, key));
        if (! hasAllKeys) {
            return;
	}
        let widget=$(`[name=save][data-id=${this.dummy}][data-instance=${this.instancetype}]`);
        widget.removeClass("d-none");
        widget.removeAttr("disabled");
    }

    // handle web socket callback
    handleCallback(message) {
        if (message.response) {
            if (message.response=="reloadpage") {
                location.reload();
                return;
            }
            if (this.widget && this.attribute in message) {
                let pk = message[this.attribute];
                console.log("replacing" + this.widget + "(" + pk + ")");
                $(`[data-widget=${this.widget}][data-id="${pk}"]`).replaceWith(message.response)
            }
        }
    }

}

