$(document).on('click', '[name=volumes][data-id]', function() {
    const objectId = $(this).data('id')  // Get the id from the button's data-id attribute
    VolumeSelection.openModal(objectId)
})
