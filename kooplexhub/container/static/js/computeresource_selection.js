// static/js/computeresource_selection.js

// Compute Resource Selection Modal Logic
(function() {
    var selectedContainerId = null
    var selectedNode = ""
    var currentNode = null
    var containerrunning = null
    var sock = null  //FIXME: monitoring

    // Handle web socket callbacks
    function nodeinfo_callback(message) {
	node = message['node']
        if (node != selectedNode) {
            console.error("out of sync? >>" + node + ">>"+selectedNode+">>")
	    return
	}
        if (node === currentNode && node != "" && containerrunning) {
		// FIXME these are not updated when modal is open!
            cpu = parseFloat($("#id_cpurequest_old").val()) + parseFloat(data["avail_cpu"]);
            gpu = parseInt($("#id_gpurequest_old").val()) + parseInt(data["avail_gpu"]);
            memory = parseFloat($("#id_memoryrequest_old").val()) + parseFloat(data["avail_memory"]);
        } else {
            cpu = message["avail_cpu"];
            gpu = message["avail_gpu"];
            memory = message["avail_memory"];
        }
        $(".progress").addClass("d-none")
        $("input[name='cpurequest']").attr("max", cpu)
        $("input[name='memoryrequest']").attr("max", memory)
        $("input[name='gpurequest']").attr("max", gpu)
        $("#thresholdhigh-cpurequest").text(cpu)
        $("#thresholdhigh-memoryrequest").text(memory)
        $("#thresholdhigh-gpurequest").text(gpu)
        $("input[name$='request'").each(function() { 
          if ($(this).attr("max") > 0) {
            $(this).attr('disabled', false ) 
          }
        })
    }

    // Handle click to show modal
    function handleClick(containerId, node) {
        selectedContainerId = containerId === "new" ? "new" : parseInt(containerId)
	const thebutton = $(`#container-resources-${containerId}`)
        if (node === "None") { node = "" }
	selectedNode = node
	currentNode = node
        $("input[name='cpurequest']").val(parseFloat(thebutton.data('cpurequest')))
        $("input[name='gpurequest']").val(parseInt(thebutton.data('gpurequest')))
        $("input[name='memoryrequest']").val(parseFloat(thebutton.data('memoryrequest')))
        $("input[name='idletime']").val(parseInt(thebutton.data('idletime')))
        $("select[name='node']").val(thebutton.data('node')).change()

	///FIXME: retrieve info if container is running
        $('.computeresource-modal').modal('show')

	sock = open_ws(wsURLs['monitor_node'], nodeinfo_callback)
    
        setTimeout(function() {
	    $("#id_node").val(node)
	    retrieveResources(node)
        }, 200);  // Timeout ensures the modal is fully visible before focusing
    }

    // Call server via websocket to fetch up to date resource information
    function retrieveResources(node) {
        sock.send(JSON.stringify({
          'request': 'monitor-node',
          'node': node,
        }))
        $(".progress").removeClass("d-none")
        $("input[name$='request'").each(function() { $(this).attr('disabled', true ) })
    }

    // Confirm compute resource selection
    function confirmSelection() {
        $('#confirm-compute-selection').on('click', function() {
            if (selectedContainerId) {
		const n = $('#id_node').val()
		const c = $('#id_cpurequest').val()
		const g = $('#id_gpurequest').val()
		const m = $('#id_memoryrequest').val()
		const i = $('#id_idletime').val()
		var changed = register_changes(selectedContainerId, 'node', n, '')
		changed = changed || register_changes(selectedContainerId, 'cpurequest', c, '')
		changed = changed || register_changes(selectedContainerId, 'gpurequest', g, '')
		changed = changed || register_changes(selectedContainerId, 'memoryrequest', m, '')
		changed = changed || register_changes(selectedContainerId, 'idletime', i, '')
		if (changed) {
		    updateButtonFace(selectedContainerId, n, c, g, m, i)
		    showSaveChanges(selectedContainerId)
		}

                // Close the modal
                $('.computeresource-modal').modal('hide');
		sock.close()
		selectedContainerId = null
            }
        });
    }

    // trigger node info retrieval in case selection changes
    function handleNodeselectChange() {
        $("#id_node").change(function() {
            $("#id_node option:selected").each(function() {
                node = $(this).attr("value")
		selectedNode = node
		retrieveResources(node)
	    })
	})
    }

    // Update button captions
    function updateButtonFace(pk, n, c, g, m, i) {
	$(`#container-resources-${pk} [name=node] [name=node_name]`).text(n) 
	$(`#container-resources-${pk} [name=cpu] [name=node_cpu_request]`).text(c)
	$(`#container-resources-${pk} [name=gpu] [name=node_gpu_request]`).text(g)
	$(`#container-resources-${pk} [name=mem] [name=node_memory_request]`).text(m + "GB")
	$(`#container-resources-${pk} [name=up] [name=node_idle]`).text(i + " h")
	$wid_node = $(`#container-resources-${pk} [name=node]`)
	$wid_cpu = $(`#container-resources-${pk} [name=cpu]`)
	$wid_gpu = $(`#container-resources-${pk} [name=gpu]`)
	$wid_mem = $(`#container-resources-${pk} [name=mem]`)
	$wid_up = $(`#container-resources-${pk} [name=up]`)
	$wid_empty = $(`#container-resources-${pk} [name=empty]`)
	if (n.length) { $wid_node.removeClass('d-none') } else { $wid_node.addClass('d-none') }
	if (c) { $wid_cpu.removeClass('d-none') } else { $wid_cpu.addClass('d-none') }
	if (g) { $wid_gpu.removeClass('d-none') } else { $wid_gpu.addClass('d-none') }
	if (m) { $wid_mem.removeClass('d-none') } else { $wid_mem.addClass('d-none') }
	if (i) { $wid_up.removeClass('d-none') } else { $wid_up.addClass('d-none') }
	if (n.length+c+g+m+i==0) { $wid_empty.removeClass('d-none') } else { $wid_empty.addClass('d-none') }
    }

    // update to be called, after server kooplex accepted new values
    function updateWidget(pk, node, cpurequest, gpurequest, memoryrequest, idletime) {
	// FIXME SAVE originals
	updateButtonFace(pk, node, cpurequest, gpurequest, memoryrequest, idletime)
    }

    // Initialize the modal logic
    function initializeComputeResourceSelection() {
        handleNodeselectChange()
        confirmSelection()
    }

    // Expose the functionality globally so it can be reused
    window.ComputeResourceSelection = {
        init: initializeComputeResourceSelection,
        openModal: handleClick,
	update: updateWidget
    }

})()

// Run when document is ready
$(document).ready(function() {
    ComputeResourceSelection.init()
});



