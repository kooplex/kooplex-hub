// static/js/xeditable.js

// Activate x-editable elements
$.fn.editable.defaults.mode = 'inline';

// Initialize editable elements
$('a.editable').each(function(){
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

// Remove default single-click editing behavior
//$('.editable').editable().off('click');

// Add double-click to manually trigger the editor
//$('.editable').on('dblclick', function(e) {
//  e.preventDefault();
//  $(this).editable('show'); // Manually trigger the editor on double-click
//});

