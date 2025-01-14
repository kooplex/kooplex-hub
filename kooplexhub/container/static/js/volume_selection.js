// static/js/volume_selection.js

// Volume Selection Modal Logic
(function() {
    var selectedObjectId = null
    var volumes_o = null

    // Parse the string as JSON to convert it to an array and set toggler to checked based on the values
    function ary_set(a, toggler) {
	if (typeof a === 'undefined') { return }
        var arr = JSON.parse(a)

        // Iterate over the array
        $.each(arr, function(index, value) {
            $(`#${toggler}-${value}`).bootstrapToggle("on")
        })
    }

    // lookup original id list
    function getOriginal(pk, binding) {
        return pk === "new" ? "[]" : $(`#original_${binding}-${pk}`).val()
    }

    // Handle click to show modal
    function handleClick(objectId) {
        selectedObjectId = objectId === "new" ? "new" : parseInt(objectId)
	volumes_o = $(`[data-pk=${selectedObjectId}][data-volumes]`).data('volumes')
        $(".configtoggle").each(function() {
	    pk = parseInt($(this).val())
	    if (volumes_o.includes(pk)) {
                $(this).bootstrapToggle("on")
	    } else {
                $(this).bootstrapToggle("off")
	    }
        })
        $('.volumes-modal').modal('show')

	// preset togglers
	ary_set(getOriginal(objectId, 'volumelist'), "volumetoggler")
    }


    // Confirm file resource selection
    function confirmSelection() {
        $('#confirm-file-selection').on('click', function() {
            if (selectedObjectId) {
                var volumes = $('[name=attach-volume]:checked').map(function() { return parseInt(this.value) }).get()

		var changed = register_changes(selectedObjectId, 'volumes', volumes, volumes_o)
		if (changed) {
		    //FIXME updateButtonFace(selectedContainerId, projects.length, courses.length, volumes.length)
		    showSaveChanges(selectedObjectId)
		}
                // Close the modal
                $('.volumes-modal').modal('hide');
		selectedObjectId = null
            }
        });
    }

    // Update button captions
    //FIXME: function updateButtonFace(pk, p, c, v) {
    //}

    // update mount lists
    function updateLists(pk, volumes) {
	if ($.isArray(volumes)) {
	    vrep=JSON.stringify(volumes.map(function (x) {return parseInt(x)}))
	    $(`#original_volumelist-${pk}`).val(vrep)
	} else {
            volumes = JSON.parse($(`#original_volumelist-${pk}`).val())
	}
	//FIXME updateButtonFace(pk, projects.length, courses.length, volumes.length)
    }

    // Initialize the modal logic
    function initializeVolumeSelection() {
        confirmSelection();
    }

    // Expose the functionality globally so it can be reused
    window.VolumeSelection = {
        init: initializeVolumeSelection,
        openModal: handleClick,
	update: updateLists,
    };

})();

// Run when document is ready
$(document).ready(function() {
    VolumeSelection.init()
})
