// static/js/project_join.js
// join a project logic

document.addEventListener("DOMContentLoaded", function() {
  const modalEl = document.getElementById('newProject');

  function cb(data) {
    if (data.response==='get-joinable') {
        $("#joinProjectSelection").replaceWith(data.replace);
	$("table[name=join-project] tbody tr").on('click', function () {
            const pk = $(this).data('id');
            wss_joinproject.send(JSON.stringify({
              request: 'join',
              pk
            }));
        });
    } else if (data.response==='join') {
        location.reload();
    }
  }


  modalEl.addEventListener('shown.bs.modal', function (event) {
    // Your logic here
    console.log("Modal is now shown:", event.target.id);
    wss_joinproject = new ManagedWebSocket(wsURLs['project_join'], {
        onMessage: cb,
    });
    wss_joinproject.send(JSON.stringify({
      request: 'get-joinable',
    }));

  });
});

