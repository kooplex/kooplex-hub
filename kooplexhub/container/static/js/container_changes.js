// static/js/container_changes.js


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


// Save changes
function save_container_config(pk) {
    pk = pk === "" ? "" : parseInt(pk)
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
    setTimeout(function() {
        wss_containerconfig.send(JSON.stringify(data))
    }, 200)
    hideSaveChanges(pk, 'container')
    // Return a promise to handle asynchronous behavior
    var deferred = $.Deferred();
    deferred.resolve();
    return deferred.promise();
}


$(document).ready(function() {
  if (wsURLs.container_config) {
    wss_containerconfig = new ManagedWebSocket(wsURLs.container_config, {
      onMessage: container_config_callback,
    })
  } 
})

