// static/js/canvascourse.js
// Canvascourse Modal Logic
document.addEventListener("DOMContentLoaded", function() {
  const modalEl = document.getElementById('newCourseModal');

  function cb(data) {
    if (data.response==='get-courses') {
        $("#canvasSelection").replaceWith(data.replace);
	$("table[name=canvas-course] tbody tr").on('click', function () {
            const pk = $(this).data('id');
            const canvas_name = $(this).data('tail');
            $("[data-id=None][data-field=name][data-instance=course]").editable('setValue', canvas_name, true)
            $("[data-id=None][data-field=description][data-instance=course]").editable('setValue', canvas_name + " imported from canvas", true)
		wss_courseconfig.register_changes('None', 'name', canvas_name, '')
		wss_courseconfig.register_changes('None', 'description', canvas_name + " imported from canvas", '')
		wss_courseconfig.register_changes('None', 'canvasid', pk, '')
        });
    } else if (data.response==='join') {
        location.reload();
    }
  }


  modalEl.addEventListener('shown.bs.modal', function (event) {
    console.log("Modal is now shown:", event.target.id);
    wss_fetchcanvas = new ManagedWebSocket(wsURLs.wss_canvas, {
        onMessage: cb,
    });
    wss_fetchcanvas.send(JSON.stringify({
      request: 'get-courses',
    }));

  });
});

