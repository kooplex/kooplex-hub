// static/js/container_changes.js


// handle web socket callback
function container_config_callback(message) {
        console.log(message)
    if (message.response && message.container_id) {
        if (message.response=="reloadpage") {
            location.reload()
            return
        }
        pk = message.container_id
	$(`[data-widget=containercard][data-id="${pk}"]`).replaceWith(message.response)
    }
}


// Save changes
function save_container_config(pk) {
    pk = pk === "None" ? "None" : parseInt(pk)
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

