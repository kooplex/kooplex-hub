(function() {
    const now = new Date()
    
    function initializeDatetimePickers() {
        // Loop through each unique `data-id` and set up the pairs
        const pairs = new Set()
        document.querySelectorAll('[name=start-datetime][data-id]').forEach(element => pairs.add(element.dataset.id))
        
        pairs.forEach(dataId => {
            // Get the start and end pickers for the current `data-id`
            const startInput = document.querySelector(`input[name="start-datetime"][data-id="${dataId}"]`)
            const endInput = document.querySelector(`input[name="end-datetime"][data-id="${dataId}"]`)
        
            const startPicker = flatpickr(startInput, {
                enableTime: true,
                dateFormat: "Y-m-d H:i",
                time_24hr: true,
                allowInput: true,
                minDate: now, // Prevent past dates
                onChange: function(selectedDates) {
                    let value=selectedDates[0]
                    if (endInput._flatpickr && value!==undefined) {
                        endInput._flatpickr.set('minDate', value)
                    }
                }
            })
        
            const endPicker = flatpickr(endInput, {
                enableTime: true,
                dateFormat: "Y-m-d H:i",
                time_24hr: true,
                allowInput: true,
                minDate: now, // Prevent past dates
                onChange: function(selectedDates) {
                    let value=selectedDates[0]
                    if (startInput._flatpickr && value!==undefined) {
                        startInput._flatpickr.set('maxDate', value)
                    }
                }
            })
        
            // Clear button functionality for this pair
            document.querySelectorAll(`.clear-btn[data-id="${dataId}"]`).forEach(button => {
                button.addEventListener('click', function() {
                    const targetInput = document.querySelector(`input[name="${this.dataset.target}"][data-id="${dataId}"]`)
                    if (targetInput) {
                        const picker = targetInput._flatpickr
                        if (picker) {
                            picker.clear()
                            // Reset constraints
                            if (this.dataset.target === 'start-datetime' && endPicker) {
                                endPicker.set('minDate', now)
                            } else if (this.dataset.target === 'end-datetime' && startPicker) {
                                startPicker.set('maxDate', null)
                            }
                        }
                    }
                })
            })
        })
    }
    
    // Expose the functionality globally so it can be reused
    window.DatetimePickers = {
        init: initializeDatetimePickers,
    }

})()
