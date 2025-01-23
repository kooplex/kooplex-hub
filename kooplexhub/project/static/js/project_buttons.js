// Show Save Changes button
showSaveNew['project']=function(pk) {
     var count = changes.filter(x => x.pk === "new"  && ["name", "subpath", "preferred_image", "description"].includes(x.field)).length
     return (count >= 4) 
}

// hide and show button faces  //FIXME: repeated code!
function applyButton(widgetId, selectedButtonName) {
    // Hide all buttons in the widget
    $(`#${widgetId} > [name]`).each(function () { $(this).hide() })

    // Show the selected button
    $(`#${widgetId} > [name=${selectedButtonName}]`).show()
}

// update project scope button's state indicator
const buttonScopeStates = {
  "public": "public",
  "private": "private",
  default: "private"
};

function updateProjectScope(projectId, scope) {
    let widgetId = `project-scope-${projectId}`
    let selectedButtonName = buttonScopeStates[scope] || buttonScopeStates["default"]
    applyButton(widgetId, selectedButtonName)
}

function projectScopeButtonClick(projectId, req) {
    projectId = projectId === "" ? "" : parseInt(projectId)
    const changed = register_changes(projectId, 'scope', req, '') // FIXME: old
    if (changed) {
        updateProjectScope(projectId, req)
	showSaveChanges(projectId)  //FIXME: instance!!
    }
}


$(document).ready(function() {
// When typing the new name, guess a folder name
$('.editable[data-field=subpath][data-id=""]').on('shown', function(e, editable) {
    editable.input.$input.on('keyup', function(event) {
        $('.editable[data-field=subpath][data-id=""]').data('typed', true)
    })
})
$('.editable[data-field=name][data-id=""]').on('shown', function(e, editable) {
    // Now attach a keyup event listener to the dynamically created input
    editable.input.$input.on('keyup', function(event) {
        if (! $('.editable[field=subpath][data-id=""]').data('typed') ) {
            $('.editable[data-field=subpath][data-id=""]').text($('.editable[data-field=name][data-id=""]').text().toLowerCase().replace(eval("/[^a-z0-9]/g"), '_'))
        }
    })
})

})
