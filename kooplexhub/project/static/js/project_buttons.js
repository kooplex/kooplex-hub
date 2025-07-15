// Show Save Changes button
showSaveNew['project']=function() {
     var count = changes.filter(x => x.pk === "None"  && ["name", "image", "description"].includes(x.field)).length
     return count>=3 
}


// Attach Save Changes Event
$(document).on('click', '[name=save][data-id][data-instance=project]', function() {
    save_project_config($(this).data('id'))
})


// hide and show button faces  //FIXME: repeated code!
function applyButton(widgetId, selectedButtonName) {
    // Hide all buttons in the widget
    $(`#${widgetId} > [name]`).each(function () { $(this).hide() })

    // Show the selected button
    $(`#${widgetId} > [name=${selectedButtonName}]`).show()
}

// handle scope button
$(document).on('click', '[data-field=scope][name][data-id]', function() {
    let pk=$(this).data('id')
    let name=$(this).attr('name')
    let req_val=name==='public'?'private':'public'
    let widgetId = `project-scope-${pk}`
    projectId = pk === "None" ? "None" : parseInt(pk)
    applyButton(widgetId, req_val)
    register_changes(projectId, 'scope', req_val, $(widgetId).data('orig'))
    showSaveChanges(projectId, 'project')
})

