// static/js/image_selection.js

// Image Selection Modal Logic
(function() {
    var selectedContainerId = null
    var selectedImageId = null
    var originalImageId = null
    var selectedIndex = -1

    // Handle image item click
    function handleImageItemClick() {
        $('.image-item').on('click', function() {
            var index = $(this).index()  // Get index of clicked item
            selectImage(index)
            $(this).focus()  // Focus on the clicked item to capture keyboard events
        })
    }

    // Helper function to check if an element is visible in a scrollable container
    function isElementVisible($container, $element) {
        var containerTop = $container.scrollTop()
        var containerBottom = containerTop + $container.height()
        var elementTop = $element.position().top + $container.scrollTop()
        var elementBottom = elementTop + $element.outerHeight()

        return elementTop >= containerTop && elementBottom <= containerBottom
    }

    // Scroll the element into view only if it is not visible
    function ensureElementInView($element) {
        var $container = $('#image-list')
        if (!(typeof $element.position() === "undefined") && !isElementVisible($container, $element)) {
            $container.scrollTop($element.position().top + $container.scrollTop() - $container.height() / 2)
        }
    }

    // Select image at a given index
    function selectImage(index) {
        // Remove the active class from any previously selected item
        $('.image-item').removeClass('active')

        // Select the image item at the given index
        var $item = $('.image-item').eq(index)
        $item.addClass('active')
        selectedImageId = $item.data('id')

        // Update the right pane
        $('#image-name').text($item.text())
        $('#image-description').text($item.data('description'))
        $('#image-thumbnail').attr("src", $item.data('thumbnail'))

        selectedIndex = index  // Update the selected index

	// Ensure the selected item is visible in the scrollable list
        ensureElementInView($item)
    }

    // Handle keyboard navigation (Up/Down arrows)
    function handleKeyboardNavigation() {
        $('#image-list').on('keydown', function(e) {
            var totalItems = $('.image-item').length

            if (e.key === 'ArrowDown') {
                // Move down (next item)
                selectedIndex = (selectedIndex + 1) % totalItems
                selectImage(selectedIndex)
            } else if (e.key === 'ArrowUp') {
                // Move up (previous item)
                selectedIndex = (selectedIndex - 1 + totalItems) % totalItems
                selectImage(selectedIndex)
            }
        })
    }

    // Handle click to show modal
    function handleClick(containerId, imageSelectedId) {
        selectedContainerId = containerId === "new" ? "new" : parseInt(containerId)
	imageId = imageSelectedId
        $('.image-modal').modal('show')
    
        // Automatically focus the image item based on the given imageId or fallback to the first item
        setTimeout(function() {
            var $item = $(`.image-item[data-id="${imageId}"]`)
            
            // If the item with the given imageId is not found, use the first item
            if ($item.length === 0) {
                $item = $('.image-item').first()
                selectedIndex = 0
                imageId = $item.data('id')  // Update the imageId with the first item's id
                $('#imageModalAlert').removeClass('d-none')  // Show the alert box
            } else {
                // Find the index of the $item in the list of image-items
                selectedIndex = $item.index()
		$('#imageModalAlert').addClass('d-none')     // Hide the alert box
            }
    
            // Focus the item and select it
            $item.focus()
            selectImage(selectedIndex)  // Select the item based on its index in the list, not its imageId
        }, 200)  // Timeout ensures the modal is fully visible before focusing
    }

    // Confirm image selection
    function confirmSelection() {
        $('#confirm-image-selection').on('click', function() {
            if (selectedContainerId && selectedImageId) {
                const changed = register_changes(selectedContainerId, 'image', selectedImageId, originalImageId) 
		if (changed) {
                    $(`[data-field=image][data-pk="${selectedContainerId}"]`).text($('#image-name').text())
                    // show the save button
                    $(`#container-save-${selectedContainerId}`).removeClass("d-none")
		}
            }
            // Close the modal
            $('.image-modal').modal('hide')
        })
    }

    // Initialize the modal logic
    function initializeImageSelection() {
        handleImageItemClick()
        handleKeyboardNavigation()
        confirmSelection()
    }

    // Expose the functionality globally so it can be reused
    window.ImageSelection = {
        init: initializeImageSelection,
        openModal: handleClick
    }

})()

// Run when document is ready
$(document).ready(function() {
    ImageSelection.init()
})

