// static/js/xeditable.js
// FIXME: code repetition

// Activate x-editable elements
$.fn.editable.defaults.mode = 'inline';

// Initialize editable elements
$('.editable').each(function(){
  $(this).editable({
    validate: function(value) {
      if ($.trim(value) === '') {
        return 'This field is required';  // Error message to display if validation fails
      }
      if ($.trim(value).length < 3) {
        return 'Please enter at least 3 characters';  // Another validation example
      }
    }
  }).on('save', function(e, params) {
    const $element = $(this)
    const pk = $element.data('pk')
    const changed = register_changes(pk, $element.data('field'), $.trim(params.newValue), $element.data('orig'))
    if (changed) {
      showSaveChanges(pk)
    }
  })

  // After showing the editable mode, replace the default icons with FontAwesome
  $(this).on('shown', function() {
    // Replace default OK button icon with FontAwesome check
    $('.editable-submit i').removeClass('icon-ok').addClass('fas fa-thumbs-up')
    // Replace default Cancel button icon with FontAwesome times
    $('.editable-cancel i').removeClass('icon-remove').addClass('fas fa-thumbs-down')
  })
})

// Initialize x-editable on the element with the `editable` class
$('p.editable').editable({
    type: 'textarea',  // Specify that this is a textarea
    rows: 3, // Specify number of rows for the textarea
    showbuttons: 'right', // Position the save/cancel buttons at the bottom
})

// Attach event listener for x-editable's shown event
$('p.editable').on('shown', function(e, editable) {
    // Replace default OK button icon with FontAwesome check
    $('.editable-submit i').removeClass('icon-ok').addClass('fas fa-thumbs-up')
    // Replace default Cancel button icon with FontAwesome times
    $('.editable-cancel i').removeClass('icon-remove').addClass('fas fa-thumbs-down')
    // Access the dynamically created textarea
    const $textarea = editable.input.$input

    // Attach keyup event listener to the textarea
    $textarea.on('keyup', function(event) {
        // Detect 'Enter' key press (without Shift) to trigger an action
        if (event.key === 'Enter' && !event.shiftKey) {
            // Trigger submission (save the changes)
            $textarea.closest('form').submit() // Or trigger x-editable's own save
        }
    })
})

// Attach event listener for x-editable's shown event
$('p.editable').on('save', function(e, params) {
    const $element = $(this)
    const pk = $element.data('pk')
    const changed = register_changes(pk, $element.data('field'), $.trim(params.newValue), $element.data('orig'))
    if (changed) {
      showSaveChanges(pk)
    }
})

// Remove default single-click editing behavior
//$('.editable').editable().off('click');

// Add double-click to manually trigger the editor
//$('.editable').on('dblclick', function(e) {
//  e.preventDefault();
//  $(this).editable('show'); // Manually trigger the editor on double-click
//});

