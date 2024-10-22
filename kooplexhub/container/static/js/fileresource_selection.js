// static/js/fileresource_selection.js

// Compute Resource Selection Modal Logic
(function() {
    var selectedContainerId = null

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
    function handleClick(containerId) {
        selectedContainerId = containerId === "new" ? "new" : parseInt(containerId)
        $(".configtoggle").each(function() {
            $(this).bootstrapToggle("off")
        })
        $('.fileresource-modal').modal('show')

	// preset togglers
	ary_set(getOriginal(containerId, 'projectlist'), "projecttoggler")
	ary_set(getOriginal(containerId, 'courselist'), "coursetoggler")
	ary_set(getOriginal(containerId, 'volumelist'), "volumetoggler")
    }


    // Confirm file resource selection
    function confirmSelection() {
        $('#confirm-file-selection').on('click', function() {
            if (selectedContainerId) {
                var projects = $('[name=attach-project]:checked').map(function() { return parseInt(this.value) }).get()
                var courses = $('[name=attach-course]:checked').map(function() { return parseInt(this.value) }).get()
                var volumes = $('[name=attach-volume]:checked').map(function() { return parseInt(this.value) }).get()
		var projects_o = JSON.parse(getOriginal(selectedContainerId, 'projectlist'))
		var courses_o = JSON.parse(getOriginal(selectedContainerId, 'courselist'))
		var volumes_o = JSON.parse(getOriginal(selectedContainerId, 'volumelist'))

		var changed = register_changes(selectedContainerId, 'projects', projects, projects_o)
		changed = changed || register_changes(selectedContainerId, 'courses', courses, courses_o)
		changed = changed || register_changes(selectedContainerId, 'volumes', volumes, volumes_o)
		if (changed) {
		    updateButtonFace(selectedContainerId, projects.length, courses.length, volumes.length)
                    // show the save button
                    $(`#container-save-${selectedContainerId}`).removeClass("d-none")
		}
                // Close the modal
                $('.fileresource-modal').modal('hide');
		selectedContainerId = null
            }
        });
    }

    // Update button captions
    function updateButtonFace(pk, p, c, v) {
	$(`#container-mounts-${pk} [name=project] [name=project_count]`).text(p) 
	$(`#container-mounts-${pk} [name=course] [name=course_count]`).text(c) 
	$(`#container-mounts-${pk} [name=volume] [name=volume_count]`).text(v) 
	$wid_project = $(`#container-mounts-${pk} [name=project]`)
	$wid_course = $(`#container-mounts-${pk} [name=course]`)
	$wid_volume = $(`#container-mounts-${pk} [name=volume]`)
	$wid_empty = $(`#container-mounts-${pk} [name=empty]`)
	if (p==0) { $wid_project.addClass('d-none') } else { $wid_project.removeClass('d-none') }
	if (c==0) { $wid_course.addClass('d-none') } else { $wid_course.removeClass('d-none') }
	if (v==0) { $wid_volume.addClass('d-none') } else { $wid_volume.removeClass('d-none') }
	if (p+v+c==0) { $wid_empty.removeClass('d-none') } else { $wid_empty.addClass('d-none') }
    }

    // update mount lists
    function updateLists(pk, projects, courses, volumes) {
	if ($.isArray(projects)) {
	    prep=JSON.stringify(projects.map(function (x) {return parseInt(x)}))
	    $(`#original_projectlist-${pk}`).val(prep)
	} else {
            projects = JSON.parse($(`#original_projectlist-${pk}`).val())
	}
	if ($.isArray(courses)) {
	    crep=JSON.stringify(courses.map(function (x) {return parseInt(x)}))
	    $(`#original_courselist-${pk}`).val(crep)
	} else {
            courses = JSON.parse($(`#original_courselist-${pk}`).val())
	}
	if ($.isArray(volumes)) {
	    vrep=JSON.stringify(volumes.map(function (x) {return parseInt(x)}))
	    $(`#original_volumelist-${pk}`).val(vrep)
	} else {
            volumes = JSON.parse($(`#original_volumelist-${pk}`).val())
	}
	updateButtonFace(pk, projects.length, courses.length, volumes.length)
    }

    // Initialize the modal logic
    function initializeFileResourceSelection() {
        $("[id^=container-mounts-]").mouseenter(function() {
            $( this ).css("cursor", "pointer")
        })
        confirmSelection();
    }

    // Expose the functionality globally so it can be reused
    window.FileResourceSelection = {
        init: initializeFileResourceSelection,
        openModal: handleClick,
	update: updateLists,
    };

})();

// Run when document is ready
$(document).ready(function() {
    FileResourceSelection.init();
});




