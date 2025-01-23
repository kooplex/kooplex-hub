///////////////////////////////////////
// Container Control button Logic

// Handle web socket callbacks
function containerbutton_callback(message) {
  if (message.replace_widgets && message.container_id) {
    let objectId=message.container_id
    $.each(message.replace_widgets, function(key, value) {
      $(`[name=${key}][data-id=${objectId}]`).replaceWith(value)
    })
  }
}

$(document).ready(function() {
  if (wsURLs.container_control) {
    wss_containercontrol = new ManagedWebSocket(wsURLs.container_control, {
      onMessage: containerbutton_callback,
    })
  }
})


// start a container
$(document).on('click', 'button[name="startcontainer"]', function () {
  const objectId = $(this).data('id'); // Get the id from the button's data-id attribute
  const command = $(this).data('command')
  wss_containercontrol.send(JSON.stringify({
    pk: objectId,
    request: command,
  }))
})


// stop a container
$(document).on('click', 'button[name="stopcontainer"]', function () {
  const objectId = $(this).data('id'); // Get the id from the button's data-id attribute
  wss_containercontrol.send(JSON.stringify({
    pk: objectId,
    request: 'stop',
  }))
})


// open a container
$(document).on('click', 'button[name="opencontainer"]', function () {
  const url = $(this).data('url') // Get the url from the button's data-url attribute
  console.log( "opening: " + url )
  var win = window.open(url, '_blank')
  if (win) {
    win.focus()
  }
})



// hide and show button faces
function applyButton(widgetId, selectedButtonName) {
    // Hide all buttons in the widget
    $(`#${widgetId} > [name]`).each(function () { $(this).hide() })

    // Show the selected button
    $(`#${widgetId} > [name=${selectedButtonName}]`).show()
}


// Show Save Changes button
showSaveNew['container']=function() {
  var count = changes.filter(x => x.pk === ""  && ["name", "image"].includes(x.field)).length
  return count<2?false:true
}


$(document).on('click', '[name=save][data-id][data-instance=container]', function() {
    save_container_config($(this).data('id'))
})


// Hide Save Changes button
function hideSaveChanges(containerId) {
  $(`[name=save][data-id="${containerId}"][data-instance=container]`).addClass("d-none")
}

// This function can be triggered initially on page load or from WebSocket events
const buttonTeleportStates = {
  "True": "revoke",
  default: "grant"
};
function updateTeleportButton(containerId, state) {
    let widgetId = `container-teleport-${containerId}`
    let selectedButtonName = buttonTeleportStates[state] || "grant"
    applyButton(widgetId, selectedButtonName)
}

function teleportButtonClick(containerId, req) {
    containerId = containerId === "new" ? "new" : parseInt(containerId)
    const changed = register_changes(containerId, 'start_teleport', req, '') // FIXME: old
    if (changed) {
        updateTeleportButton(containerId, req)
	showSaveChanges(containerId, 'container')
    }
}

// This function can be triggered initially on page load or from WebSocket events
const buttonSeafileStates = {
  "True": "revoke",
  default: "grant"
};
function updateSeafileButton(containerId, state) {
    let widgetId = `container-seafile-${containerId}`
    let selectedButtonName = buttonSeafileStates[state] || "grant"
    applyButton(widgetId, selectedButtonName)
}

function seafileButtonClick(containerId, req) {
    containerId = containerId === "new" ? "new" : parseInt(containerId)
    const changed = register_changes(containerId, 'start_seafile', req, '') // FIXME: old
    if (changed) {
        updateSeafileButton(containerId, req)
	showSaveChanges(containerId, 'container')
    }
}

