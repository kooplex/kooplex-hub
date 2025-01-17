// static/js/fetchlogs.js
// Container logs Modal Logic

// Handle web socket callbacks
function fetchlog_callback(message) {
  $("#container-log").text(message['podlog'])
  $("#container-log").scrollTop($("#container-log")[0].scrollHeight)
  $(".progress").addClass("d-none")
}

$(document).ready(function() {
  sock_fetchlog = open_ws(wsURLs['container_fetchlog'], fetchlog_callback)
})


$(document).on('click', '[data-bs-target="#fetchlogsModal"]', function () {
  const objectId = $(this).data('id'); // Get the id from the button's data-id attribute
  $("#container-log").text("Retrieving container logs. It may take a while to download...")
  $(".progress").removeClass("d-none")
  sock_fetchlog.send(JSON.stringify({
    pk: objectId,
    request: 'container-log',
  }))
})

