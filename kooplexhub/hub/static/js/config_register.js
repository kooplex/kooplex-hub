// static/js/config_register.js


// keep track of changes
let changes = []
let showSaveNew = {}


// Check equality of two arrays
function arraysEqual(arr1, arr2) {
    // Check if the arrays have the same length
    if (arr1.length !== arr2.length) {
        return false
    }
    // Sort both arrays and compare them element by element
    var sortedArr1 = arr1.slice().sort((a, b) => a - b) // Sort a copy of arr1
    var sortedArr2 = arr2.slice().sort((a, b) => a - b) // Sort a copy of arr2
    // Check if all elements are equal
    for (var i = 0; i < sortedArr1.length; i++) {
        if (sortedArr1[i] !== sortedArr2[i]) {
            return false
        }
    }
    // If all checks passed, the arrays are equal
    return true
}


// Configuration logic
function register_changes(pk, fieldName, newValue, oldValue) {
    //pk=(pk===undefined || pk===NaN)?"None":pk
    pk=(pk === null || pk === undefined || pk === "" || (typeof pk === "number" && isNaN(pk)))?"None":pk
    var changed = $.isArray(newValue) ? ! arraysEqual(newValue, oldValue) : oldValue !== newValue
    if (changed) {
        // Check if the change already exists
        const existingChangeIndex = changes.findIndex(change => change.pk === pk && change.field === fieldName)

        if (existingChangeIndex !== -1) {
            // Update the existing change
            changes[existingChangeIndex].newValue = newValue
        } else {
            // Add a new change
            changes.push({
                pk: pk,
                field: fieldName,
                newValue: newValue
            })
        }
        return true
    } else {
        return false
    }
}


// Show Save Changes button
function showSaveChanges(pk, instance) {
  //pk=(pk===undefined)?"":pk
  pk=(pk === null || pk === undefined || pk === "" || (typeof pk === "number" && isNaN(pk)))?"None":pk
  if ((pk === "None") && !showSaveNew[instance]()) {
       return
  }
  let widget=$(`[name=save][data-id="${pk}"][data-instance=${instance}]`)
  widget.removeClass("d-none")
  widget.removeAttr("disabled")
}


// Hide Save Changes button
function hideSaveChanges(pk, instance) {
  //pk=(pk===undefined)?"":pk
  pk=(pk === null || pk === undefined || pk === "" || (typeof pk === "number" && isNaN(pk)))?"None":pk
  $(`[name=save][data-id="${pk}"][data-instance=${instance}]`).addClass("d-none")
}

