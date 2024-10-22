 
// update container image button's state indicator
function updateContainerState(container_id, state) {
  $(`[name=phase][data-pk=${container_id}]`).html(state)
}

// update container image button's name field
function container_image_update_name(container_id, image) {
  $(`#container-image-${widget_id} > [name=name]`).html(image)
}


// update container name
function updateContainerName(container_id, value) {
  $(`a.editable[data-pk=${container_id}]`).text(value)
}


// hide and show button faces
function applyButton(widgetId, selectedButtonName) {
    // Hide all buttons in the widget
    $(`#${widgetId} > [name]`).each(function () { $(this).hide() })

    // Show the selected button
    $(`#${widgetId} > [name=${selectedButtonName}]`).show()
}

// Update button_start state based on the container state
const buttonStartStates = {
  run: "restart",
  restart: "restart",
  np: "start",
  starting: "busy",
  default: "default"
};

function updateButtonStartState(containerId, suffix, state) {
    let widgetId = `container-start-${containerId}${suffix}`
    let selectedButtonName = buttonStartStates[state] || "default"  // Fallback to default if state is unknown
    applyButton(widgetId, selectedButtonName)
}

// Update button_stop state based on the container state
const buttonStopStates = {
  run: "stop",
  restart: "stop",
  starting: "stop",
  np: "disabled",
  default: "default"
};

function updateButtonStopState(containerId, suffix, state) {
    let widgetId = `container-stop-${containerId}${suffix}`
    let selectedButtonName = buttonStopStates[state] || "default"  // Fallback to default if state is unknown
    applyButton(widgetId, selectedButtonName)
}

// Update button_open state based on the container state
const buttonOpenStates = {
  run: "open",
  restart: "open",
  default: "default"
};

function updateButtonOpenState(containerId, suffix, state) {
    let widgetId = `container-open-${containerId}${suffix}`
    let selectedButtonName = buttonOpenStates[state] || "default"  // Fallback to default if state is unknown
    applyButton(widgetId, selectedButtonName)
}

// Update button_fetchlogs state based on the container state
const buttonFetchlogStates = {
  run: "fetch",
  restart: "fetch",
  default: "default"
};

function updateButtonFetchlogState(containerId, suffix, state) {
    let widgetId = `container-log-${containerId}${suffix}`
    let selectedButtonName = buttonFetchlogStates[state] || "default"  // Fallback to default if state is unknown
    applyButton(widgetId, selectedButtonName)
}

// open a container
function open_container(containerId) {
  var url = $( "#url-containeropen-" + containerId).val()
  var win = window.open(url, '_blank')
  if (win) {
    win.focus()
  }
}


// Show restart reason badge and update tooltip
function updateRestartReason(containerId, tooltip) {
    $(`#container-restartreason-${containerId}`).attr('title', tooltip)
    $(`#container-restartreason-${containerId}`).removeClass('d-none')
}

// Hide restart reason badge
function hideRestartReason(containerId) {
    $(`#container-restartreason-${containerId}`).addClass('d-none')
}


// This function can be triggered initially on page load or from WebSocket events
function updateButtons(containerId, suffix, initialState) {
    updateButtonStartState(containerId, suffix, initialState)
    updateButtonStopState(containerId, suffix, initialState)
    updateButtonOpenState(containerId, suffix, initialState)
    updateButtonFetchlogState(containerId, suffix, initialState)
    if (initialState === 'np') {
	hideRestartReason(containerId)
    }
}

// Show Save Changes button
function showSaveChanges(containerId) {
  if (containerId === "new") {
     // only show if the compulsory attributes are set
     var count = changes.filter(x => x.pk === "new"  && ["name", "image"].includes(x.field)).length
     if (count < 2) {
       return
     }
  }
  $(`#container-save-${containerId}`).removeClass("d-none")
}

// Hide Save Changes button
function hideSaveChanges(containerId) {
  $(`#container-save-${containerId}`).addClass("d-none")
}

// This function can be triggered initially on page load or from WebSocket events
const buttonTeleportStates = {
  true: "revoke",
  default: "grant"
};
function updateTeleportButton(containerId, state) {
    let widgetId = `container-teleport-${containerId}`
    let selectedButtonName = buttonTeleportStates[state] || "grant"  // Fallback to default if state is unknown
    applyButton(widgetId, selectedButtonName)
}

function teleportButtonClick(containerId, req) {
    containerId = containerId === "new" ? "new" : parseInt(containerId)
    const changed = register_changes(containerId, 'start_teleport', req, '') // FIXME: old
    if (changed) {
        updateTeleportButton(containerId, req)
	showSaveChanges(containerId)
    }
}

// This function can be triggered initially on page load or from WebSocket events
const buttonSeafileStates = {
  true: "revoke",
  default: "grant"
};
function updateSeafileButton(containerId, state) {
    let widgetId = `container-seafile-${containerId}`
    let selectedButtonName = buttonSeafileStates[state] || "grant"  // Fallback to default if state is unknown
    applyButton(widgetId, selectedButtonName)
}

function seafileButtonClick(containerId, req) {
    containerId = containerId === "new" ? "new" : parseInt(containerId)
    const changed = register_changes(containerId, 'start_seafile', req, '') // FIXME: old
    if (changed) {
        updateSeafileButton(containerId, req)
	showSaveChanges(containerId)
    }
}

