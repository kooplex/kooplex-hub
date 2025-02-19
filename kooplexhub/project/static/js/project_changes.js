// static/js/project_changes.js

// handle web socket callback
function project_config_callback(message) {
        console.log(message.project_id)
    if (message.response==="reloadpage") {
        location.reload()
    }
    let pk = message.project_id
    $(`div[id=card-${pk}`).replaceWith(message.response)
}


// Save chanegs
function save_project_config(pk) {
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
        request: 'configure-project',
        changes: changeObject
    }
    setTimeout(function() {
        wss_projectconfig.send(JSON.stringify(data))
    }, 200)
    hideSaveChanges(pk, 'project')
    // Return a promise to handle asynchronous behavior
    var deferred = $.Deferred()
    deferred.resolve()
    return deferred.promise()
}


$(document).ready(function() {
  if (wsURLs.project_config) {
    wss_projectconfig = new ManagedWebSocket(wsURLs.project_config, {
      onMessage: project_config_callback,
    })
  } 
})
