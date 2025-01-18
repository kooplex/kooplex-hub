// static/js/environments.js

//<script src="{% static 'js/container_buttons.js' %}"></script>
// open websocket for data retrieval
$(document).ready(function() {
  if (wsURLs.get_containers) {
    sock_fetch_containers = open_ws(wsURLs.get_containers, refresh_environmenttable)
  } 
})


// wss callback handler
function refresh_environmenttable(message) {
  if (message.response) {
    $("#environmentControl").replaceWith(message.response)
  }
}


// attech button click event handler
$(document).on('click', '[data-bs-target="#environmentsModal"]', function () {
  const objectId = $(this).data('id'); // Get the id from the button's data-id attribute
  $("#environmentControl").html('<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>')

  // Send the requested resource id via WebSocket to kooplex
  var data = {
      pk: objectId,
  }
  setTimeout(function() {
      sock_fetch_containers.send(JSON.stringify(data))
  }, 200)
})

