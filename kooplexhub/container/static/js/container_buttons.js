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
  wss_containercontrol.send(JSON.stringify({
    pk: objectId,
    request: 'start',
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


// restart a container
$(document).on('click', 'button[name="restartcontainer"]', function () {
  const objectId = $(this).data('id'); // Get the id from the button's data-id attribute
  wss_containercontrol.send(JSON.stringify({
    pk: objectId,
    request: 'restart',
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
    let button=$(`#${widgetId} > [name=${selectedButtonName}]`)
    button.show()
    button.removeClass('d-none')
}


// Show Save Changes button
showSaveNew['container']=function() {
  var count = changes.filter(x => x.pk === "None"  && ["name", "image"].includes(x.field)).length
  return count>=2
}


$(document).on('click', '[name=save][data-id][data-instance=container]', function() {
    save_container_config($(this).data('id'))
})


// handle teleport button
$(document).on('click', '[data-field=start_teleport][name][data-id]', function() {
    let pk=$(this).data('id')
    let name=$(this).attr('name')
    let widgetId = `container-teleport-${pk}`
    containerId = pk === "None" ? "None" : parseInt(pk)
    applyButton(widgetId, name==='grant'?'revoke':'grant')
    register_changes(containerId, 'start_teleport', name, $(widgetId).data('orig'))
    showSaveChanges(containerId, 'container')
})


// handle seafile button
$(document).on('click', '[data-field=start_seafile][name][data-id]', function() {
    let pk=$(this).data('id')
    let name=$(this).attr('name')
    let widgetId = `container-seafile-${pk}`
    containerId = pk === "None" ? "None" : parseInt(pk)
    applyButton(widgetId, name==='grant'?'revoke':'grant')
    register_changes(containerId, 'start_seafile', name, $(widgetId).data('orig'))
    showSaveChanges(containerId, 'container')
})

