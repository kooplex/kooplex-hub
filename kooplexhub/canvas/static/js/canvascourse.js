// static/js/canvascourse.js
// Canvascourse Modal Logic

// Handle web socket callbacks
function fetchcanvas_callback(message) {
  $("#canvascourseSelection").replaceWith(message["response"])
}

$(document).ready(function() {
  if (wsURLs.wss_canvas) {
    wss_fetchcanvas = new ManagedWebSocket(wsURLs.wss_canvas, {
      onMessage: fetchcanvas_callback,
    })
  }
})


$(document).on('click', '[data-bs-target="#canvascoursesModal"]', function () {
  $("#canvascourseSelection").replaceWith('<div id="canvascourseSelection" class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>')
    setTimeout(function() {
    wss_fetchcanvas.send(JSON.stringify({}))
    }, 200)
})

$(document).on('click', 'tr[data-id]', function() {
  let objectId=$(this).data('id')
  let name=$(this).data('tail')
  $('tr[data-id]').each(function() {
    if ($(this).data('id') == objectId) {
      $(this).addClass('bg-secondary text-light')
    } else {
      $(this).removeClass('bg-secondary text-light')
    }
  })
  $('#canvascourseSelection').data('selected', objectId)
  register_changes('', 'canvasid', objectId, '')
  register_changes('', 'name', name, '')
  //register_changes('', 'folder', name.replaceAll(' ', '_').toLowerCase().normalize("NFD").replace(/[\.\u0300-\u036f]/g, ""), '')
  showSaveChanges('', 'course')
})
