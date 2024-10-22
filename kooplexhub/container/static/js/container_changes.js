// static/js/container_changes.js

// keep track of changes
let changes = []

// FIXME: somewhere more common
// Check equality of two arrays
function arraysEqual(arr1, arr2) {
    // Check if the arrays have the same length
    if (arr1.length !== arr2.length) {
        return false;
    }
    // Sort both arrays and compare them element by element
    var sortedArr1 = arr1.slice().sort((a, b) => a - b); // Sort a copy of arr1
    var sortedArr2 = arr2.slice().sort((a, b) => a - b); // Sort a copy of arr2
    // Check if all elements are equal
    for (var i = 0; i < sortedArr1.length; i++) {
        if (sortedArr1[i] !== sortedArr2[i]) {
            return false;
        }
    }
    // If all checks passed, the arrays are equal
    return true;
}

// Container configuration logic
function register_changes(pk, fieldName, newValue, oldValue) {
    var changed = $.isArray(newValue) ? ! arraysEqual(newValue, oldValue) : oldValue !== newValue
    if (changed) {
        // Check if the change already exists
        const existingChangeIndex = changes.findIndex(change => change.pk === pk && change.field === fieldName)

        if (existingChangeIndex !== -1) {
            // Update the existing change
            changes[existingChangeIndex].newValue = newValue
        } else {
            // Add a new change
            changes.push({
                pk: pk,
                field: fieldName,
                newValue: newValue
            })
        }
        return true
    } else {
        return false
    }
}


// handle web socket callback
function container_config_callback(message) {
        console.log(message)
    if (message.response) {
        const resp=message.response
	if (resp.reloadpage) {
            location.reload()
	    return
	}
        pk = resp.container_id
        if (resp.restart) {
            updateRestartReason(pk, resp.restart)
        }
        if (resp.success) {
            const s = resp.success
	    projects = s.projects ? s.projects.projects : "dummy"
	    courses = s.courses ? s.courses.courses : "dummy"
	    volumes = s.volumes ? s.volumes.volumes : "dummy"
            FileResourceSelection.update(pk, projects, courses, volumes)
        }
	if (resp.failed) {
	    const f = resp.failed
	    if (f.name) {
		updateContainerName(pk, f.name.value)
	        alert(f.name.error)
	    } else {
                //FIXME: ANYTHING UNHANDLED
		console.log("unhandled failures", f)
	    }
	}
    }
}


// Save chanegs
function save_container_config(pk) {
    pk = pk === "new" ? "new" : parseInt(pk)
    console.log(pk)
    // Object to represent the changes
    var changeObject = { }
    // Iterate and pop elements where pk equals s
    for (var i = changes.length - 1; i >= 0; i--) {
        if (changes[i].pk === pk) {
            // Use the field as the key and newValue as the value
            changeObject[changes[i].field] = changes[i].newValue;
            // Remove the element from the original array
            changes.splice(i, 1)
        }
    }

    // Send the updated value via WebSocket to kooplex
    var data = {
        pk: pk,
        request: 'configure-container',
        changes: changeObject
    }
    sock = open_ws(wsURLs['container_config'], container_config_callback)
    setTimeout(function() {
        sock.send(JSON.stringify(data))
    }, 200)
    hideSaveChanges(pk)
    // Return a promise to handle asynchronous behavior
    var deferred = $.Deferred();
    deferred.resolve();
    return deferred.promise();
}

