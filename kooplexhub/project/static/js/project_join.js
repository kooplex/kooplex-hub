// static/js/project_join.js
// join a project logic

// Handle web socket callbacks
function fetchprojects_callback(message) {
  $("#projectSelection").replaceWith(message["response"])
}

$(document).ready(function() {
  wss_fetchprojects = new ManagedWebSocket(wsURLs['project_joinable'], {
    onMessage: fetchprojects_callback,
  })
  wss_joinproject = new ManagedWebSocket(wsURLs['project_join'], {})
})


$(document).on('click', '[data-bs-target="#fetchlogsModal"]', function () {
  const objectId = $(this).data('id'); // Get the id from the button's data-id attribute
  $("#container-log").text("Retrieving container logs. It may take a while to download...")
  $(".progress").removeClass("d-none")
  wss_fetchlog.send(JSON.stringify({
    pk: objectId,
    request: 'container-log',
  }))
})


$(document).on('click', '[data-bs-target="#joinprojectModal"]', function () {
  $("#projectSelection").replaceWith('<div id="projectSelection" class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>')
  setTimeout(function() {
    wss_fetchprojects.send(JSON.stringify({}))
  }, 200)
})

$(document).on('click', 'tr[data-id]', function() {
  objectId=$(this).data('id')
  $('tr[data-id]').each(function() {
    if ($(this).data('id') == objectId) {
      $(this).addClass('bg-secondary text-light')
    } else {
      $(this).removeClass('bg-secondary text-light')
    }
  })
  let saveWidget=$('[name=save][data-id=""][data-instance=joinproject]')
   saveWidget.removeAttr('disabled')
   saveWidget.data('selected', objectId)
})

$(document).on('click', '[name=save][data-id=""][data-instance=joinproject]', function () {
    wss_joinproject.send(JSON.stringify({
	pk: $(this).data('selected')
    }))
})
