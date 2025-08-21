// Show Save Changes button
//     let req=$('#canvascoursesModal').hasClass('show')?["name", "image", "description", "canvasid"]:["name", "image", "description"]

$(document).ready(function() {
  if (wsURLs.course_config) {
    wss_courseconfig = new ConfigHandler(wsURLs.course_config, 'configure-course', 'coursecard', 'course', 'course_id', ['name', 'image', 'description']);
  } 
})


$(document).on('click', '[name=assignment][data-id]', function() {
    let pk = $(this).data('id')
    AssignmentHandler.openModal(pk)
})


$(document).on('click', '[name="save"][data-id][data-instance=course]', function() {
    wss_courseconfig.createnew();
})


