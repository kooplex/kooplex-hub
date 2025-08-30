// environments.js

//<script src="{% static 'js/container_buttons.js' %}"></script>
// open websocket for data retrieval
$(document).ready(function() {
  if (wsURLs.get_containers) {
    wss_fetchcontainers = new ManagedWebSocket(wsURLs.get_containers, {
      onMessage: refresh_environmenttable,
    })
  } 
})


// wss callback handler
function refresh_environmenttable(message) {
  if (message.response && message.pk) {
    $(`#environmentControl-${message.pk}`).replaceWith(message.response)
  } else if (message.response) {
    $("#environmentControl").replaceWith(message.response)
  }
}

// attach button click event handler
$(document).on('click', '[id^=environmentControl-][data-id][data-autoadd]', function () {
  const objectId = $(this).data('id'); // Get the id from the button's data-id attribute
  $(`#environmentControl-${objectId}`).replaceWith(`<div id="environmentControl-${objectId}" class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>`)

  // Send the requested resource id via WebSocket to kooplex
  var data = {
      pk: objectId,
      request: 'autoadd',
  }
  setTimeout(function() {
      wss_fetchcontainers.send(JSON.stringify(data))
  }, 200)
})

