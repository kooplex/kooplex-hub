// User Selection Modal Logic
(function() {
    var pk = null
    var instance = null
    var selectedUserIds = null
    var originalUserIds = null
    var markedUserIds = null
    var originalMarkedIds = null
    const users = []

    // Initialize users object
    function initUsers() {
        // Parse the JSON data from the <script> tag
        const usersData = JSON.parse(document.getElementById('users_data').textContent)

        // Loop through each item in usersData to structure the objects
        usersData.forEach(userDict => {
            // Extract the PK and user details
            const pk = Object.keys(userDict)[0] // Get the first (and only) key, which is the PK
            const userDetails = userDict[pk] // Get the user's details

            // Construct a new user object
            users.push({
                pk: parseInt(pk),
                name_and_username: userDetails.name_and_username,
                search: userDetails.search
            })
        })

	// hide search results
        $('#user-search-results').hide()
	initTogglers()
    }

    // Handle search bar input
    $('#search-user').on('input', function () {
        const query = $(this).val().toLowerCase().trim().replaceAll(' ', '')
        if (query) {
            const matches = users.filter(user =>
                selectedUserIds.indexOf(user.pk) == -1 && user.search.includes(query)
            ).slice(0, 5) // Limit to top 5 matches

            $('#user-search-results').empty().show() // Clear previous results and show dropdown
            matches.forEach(user => {
                $('#user-search-results').append(
                    `<li class="list-group-item list-group-item-action" onclick="UserSelection.addUser(${user.pk})">
                         ${user.name_and_username}
                     </li>`
                )
            })
        } else {
            $('#user-search-results').hide()
        }
    })

    // Handle removal
    function handleRemoveClick(pk) {
        $(`tr[data-id=${pk}]`).hide()
	selectedUserIds = $.grep(selectedUserIds, function(value) {
            return value != pk
        })
    }

    // Handle addition
    function handleAddition(pk) {
        selectedUserIds.push(pk)
        const is_marked = $(`input[data-id=${pk}]`).prop('checked')
        if (is_marked) {
            markedUserIds.push(pk)
        } else {
            markedUserIds = $.grep(markedUserIds, function(value) {
                return value != pk
            })
        }

        $(`tr[data-id=${pk}]`).show()
        $('#search-user').val('')
        $('#user-search-results').hide()
    }

    // Handle modal open
    function handleOpen(objectId, kind) {
        pk = objectId==="None" ?"None":parseInt(objectId)
        instance=$(".users-modal").data('instance')
	selectedUserIds = $(`[name="users"][data-id="${objectId}"][data-kind="${kind}"][data-users]`).data('users').slice()
	originalUserIds = $(`[name="users"][data-id="${objectId}"][data-kind="${kind}"][data-users]`).data('users')
        markedUserIds = $(`[name="users"][data-id="${objectId}"][data-kind="${kind}"][data-marked]`).data('marked').slice()
	originalMarkedIds = $(`[name="users"][data-id="${objectId}"][data-kind="${kind}"][data-marked]`).data('marked')
	$('tr[data-id]').each(function() {
            const pk = $(this).data('id')

            // Show row if pk is in users list, hide otherwise
            if (selectedUserIds.includes(pk)) {
                $(this).show()
            } else {
                $(this).hide()
            }

            // Find the toggle button within the row
            const toggleButton = $(this).find(`input[name=usermarker][data-id=${pk}]`)
            // Check if pk is in marked list
            if (markedUserIds.includes(pk)) {
                toggleButton.bootstrapToggle('on')
	    } else {
                toggleButton.bootstrapToggle('off')
	    }
        })
        $(".users-modal").modal('show')
    }

    // Handle toggle changes
    function initTogglers() {
        $(document).on("change", "[data-toggle='toggle'][name=usermarker]", function() {
            let isChecked = $(this).prop("checked")  // Get new state (true/false)
            const pk = $(this).data('id')
            if (isChecked) {
                markedUserIds.push(pk)
            } else {
                markedUserIds = $.grep(markedUserIds, function(value) {
                    return value != pk
                })
            }
        })
    }

    // Confirm user selection
    $('#confirm-users-selection').on('click', function() {
        if (pk) {
            var changed = register_changes(pk, 'marked', markedUserIds, originalMarkedIds)
	    if (changed) {
                register_changes(pk, 'users', selectedUserIds, []) // we have to enforce listing users
	    } else {
                changed = register_changes(pk, 'users', selectedUserIds, originalUserIds) // otherwise if no change to former marking
	    }
            if (changed) {
		let userlist = users.filter(user => selectedUserIds.includes(user.pk)).map(user => user.name_and_username).join("<br>")
		    alert ("egyelore nem frissiti itt a listát, de a savere rendben lesz")
		//$(`div[data-id="${pk}"] [class=content][name=userlist]`).html(userlist)  //FIXME: use div /class; better rendering
                showSaveChanges(pk, instance)
            }
            // Close the modal
            $('.users-modal').modal('hide')
            pk=null
        }
    })


    // Expose the functionality globally so it can be reused
    window.UserSelection = {
	init: initUsers,
        openModal: handleOpen,
	addUser: handleAddition,
        removeUser: handleRemoveClick
    }

})()

$(document).on('click', '[name=remove][data-id][data-remove=user]', function() {
    UserSelection.removeUser($(this).data('id'))
})

$(document).ready(function () {
     UserSelection.init()
})

