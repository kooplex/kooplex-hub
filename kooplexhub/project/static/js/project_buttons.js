// Show Save Changes button
//function showSaveChanges(projectId) {
//  if (projectId === "new") {
//     // only show if the compulsory attributes are set
//     var count = changes.filter(x => x.pk === "new"  && ["name", "subpath", "preferred_image", "description"].includes(x.field)).length
//     if (count < 4) {
//       return
//     }
//  }
//  $(`#project-save-${projectId}`).removeClass("d-none")
//}

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
$(".editable[data-field=subpath][data-pk=new]").on('shown', function(e, editable) {
    editable.input.$input.on('keyup', function(event) {
        $(".editable[data-field=subpath][data-pk=new]").data('typed', true)
    })
})
$(".editable[data-field=name][data-pk=new]").on('shown', function(e, editable) {
    // Now attach a keyup event listener to the dynamically created input
    editable.input.$input.on('keyup', function(event) {
        if (! $(".editable[field=subpath][data-pk=new]").data('typed') ) {
            $(".editable[data-field=subpath][data-pk=new]").text($(".editable[data-field=name][data-pk=new]").text().toLowerCase().replace(eval("/[^a-z0-9]/g"), '_'))
        }
    })
})

})
