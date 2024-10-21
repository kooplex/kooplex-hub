// static/js/fetchlogs.js

// Container logs Modal Logic
(function() {
    var selectedContainerId = null
    var sock = null

    // Handle web socket callbacks
    function fetchlog_callback(message) {
        $("#container-log").text(message['podlog'])
	$("#container-log").scrollTop($("#container-log")[0].scrollHeight)
        $(".progress").addClass("d-none")
	sock.close()
	selectedContainerId = null
    }

    // Handle double-click to show modal
    function handleClick(containerId) {
        selectedContainerId = containerId
        $('.containerlogs-modal').modal('show')
        $("#container-log").text("Retrieving container logs. It may take a while to download...")
    
        sock = open_ws(wsURLs['container_fetchlog'], fetchlog_callback)

        $(".progress").removeClass("d-none")
        setTimeout(function() {
	  sock.send(JSON.stringify({
            pk: selectedContainerId,
            request: 'container-log',
          }))
        }, 500);  // Timeout ensures the modal is fully visible before sending request
    }

    // Expose the functionality globally so it can be reused
    window.ContainerLogs = {
        openModal: handleClick
    };

})();

// Run when document is ready
//$(document).ready(function() {
//});




