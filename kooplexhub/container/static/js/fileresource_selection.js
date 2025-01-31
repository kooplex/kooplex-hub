// static/js/fileresource_selection.js

// FileSystem Resource Selection Modal Logic
(function() {
    var selectedContainerId = null

    // Parse the string as JSON to convert it to an array and set toggler to checked based on the values
    function ary_set(arr, toggler) {
        // Iterate over the array
        $.each(arr, function(index, value) {
            $(`#${toggler}-${value}`).bootstrapToggle("on")
        })
    }

    // lookup original id list
    function getOriginal(pk, binding) {
	return $(`[name=mount][data-id="${pk}"]`).data(binding)
    }

    // lookup original id list
    function overwriteOriginal(pk, binding, value) {
	$(`[name=mount][data-id="${pk}"]`).data(binding, value)
    }

    // Handle click to show modal
    function handleClick(containerId) {
        selectedContainerId = containerId === "" ? "" : parseInt(containerId)
        $(".configtoggle").each(function() {
            $(this).bootstrapToggle("off")
        })
        $('.fileresource-modal').modal('show')

	// preset togglers
	ary_set(getOriginal(containerId, 'projects'), "projecttoggler")
	ary_set(getOriginal(containerId, 'courses'), "coursetoggler")
	ary_set(getOriginal(containerId, 'volumes'), "volumetoggler")
    }


    // Confirm file resource selection
    function confirmSelection() {
        if (selectedContainerId!=null) {
            var projects = $('[name=attach-project]:checked').map(function() { return parseInt(this.value) }).get()
            var courses = $('[name=attach-course]:checked').map(function() { return parseInt(this.value) }).get()
            var volumes = $('[name=attach-volume]:checked').map(function() { return parseInt(this.value) }).get()
	    var projects_o = getOriginal(selectedContainerId, 'projects')
	    var courses_o = getOriginal(selectedContainerId, 'courses')
	    var volumes_o = getOriginal(selectedContainerId, 'volumes')
            overwriteOriginal(selectedContainerId, 'projects', projects)
            overwriteOriginal(selectedContainerId, 'courses', courses)
            overwriteOriginal(selectedContainerId, 'volumes', volumes)

	    var changed = register_changes(selectedContainerId, 'projects', projects, projects_o)
	    changed = changed || register_changes(selectedContainerId, 'courses', courses, courses_o)
	    changed = changed || register_changes(selectedContainerId, 'volumes', volumes, volumes_o)
	    if (changed) {
	        updateButtonFace(selectedContainerId, projects.length, courses.length, volumes.length)
	        showSaveChanges(selectedContainerId, $(this).data('instance'))
	    }
            // Close the modal
            $('.fileresource-modal').modal('hide');
	    selectedContainerId = null
        }
    }

    // Update button captions
    function updateButtonFace(pk, p, c, v) {
	$(`[name=mount][data-id="${pk}"] [name=project_count]`).text(p) 
	$(`[name=mount][data-id="${pk}"] [name=course_count]`).text(c) 
	$(`[name=mount][data-id="${pk}"] [name=volume_count]`).text(v) 
	$wid_project = $(`[name=mount][data-id="${pk}"] [name=project]`)
	$wid_course = $(`[name=mount][data-id="${pk}"] [name=course]`)
	$wid_volume = $(`[name=mount][data-id="${pk}"] [name=volume]`)
	$wid_empty = $(`[name=mount][data-id="${pk}"] [name=empty]`)
	if (p==0) { $wid_project.addClass('d-none') } else { $wid_project.removeClass('d-none') }
	if (c==0) { $wid_course.addClass('d-none') } else { $wid_course.removeClass('d-none') }
	if (v==0) { $wid_volume.addClass('d-none') } else { $wid_volume.removeClass('d-none') }
	if (p+v+c==0) { $wid_empty.removeClass('d-none') } else { $wid_empty.addClass('d-none') }
    }


    // Initialize the modal logic
    function initializeFileResourceSelection() {
	$(document).on('mouseenter', 'button[name=mount][data-id]', function() {
            $(this).css("cursor", "pointer")
        })
	$(document).on('click', 'button[name=mount][data-id]', function() {
            handleClick($(this).data('id'))
        })
        $(document).on('click', 'button[id=confirm-file-selection]', confirmSelection )
    }

    // Expose the functionality globally so it can be reused
    window.FileResourceSelection = {
        init: initializeFileResourceSelection,
        openModal: handleClick,
    }

})()

// Run when document is ready
$(document).ready(function() {
    FileResourceSelection.init();
})




