// Show Save Changes button
showSaveNew['course']=function() {
     let req=$('#canvascoursesModal').hasClass('show')?["name", "image", "description", "canvasid"]:["name", "image", "description"]
     var count = changes.filter(x => x.pk === "None"  && req.includes(x.field)).length
     return count>=req.length
}

// handle web socket callback
function course_config_callback(message) {
    if (message.response && message.course_id) {
        if (message.response=="reloadpage") {
            location.reload()
            return
        }
	$(`[data-widget=coursecard][data-id="${message.course_id}"]`).replaceWith(message.response)
    }
}


$(document).ready(function() {
  if (wsURLs.course_config) {
    wss_courseconfig = new ManagedWebSocket(wsURLs.course_config, {
      onMessage: course_config_callback,
    })
  } 
})

// Save changes  FIXME: common code, put in util
function save_course_config(pk) {
    //pk = pk === "" ? "" : parseInt(pk)
    pk=(pk === null || pk === undefined || pk === "" || (typeof pk === "number" && isNaN(pk)))?"None":pk
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
        changes: changeObject
    }
    setTimeout(function() {
        wss_courseconfig.send(JSON.stringify(data))
    }, 200)
    // Return a promise to handle asynchronous behavior
    var deferred = $.Deferred();
    deferred.resolve();
    return deferred.promise();
}


$(document).on('click', '[name=assignment][data-id]', function() {
    let pk = $(this).data('id')
    AssignmentHandler.openModal(pk)
})


$(document).on('click', '[name="save"][data-id][data-instance=course]', function() {
    const pk = $(this).data('id')
    save_course_config(pk)
    hideSaveChanges(pk, 'course')
})


$(document).on('click', '[name=users][data-id][data-kind]', function() {
    const objectId = $(this).data('id')  // Get the id from the button's data-id attribute
    const kind = $(this).data('kind')  // Get the id from the button's data-id attribute
    UserSelection.openModal(objectId, kind)
})

