let selectedCell  // Track which cell was clicked
let student       // Track selected student
let assignment    // Track selected assignment


// Rewrite comment input field, with data from server 
function receiveComment(data) {
    if ((data.student == student) && (data.assignment == assignment)) {
        $("#popup-comment").val(data.comment)
    }
}


// Show popup when a cell is clicked
$(document).on("click", "td[data-editable='true']", function (e) {
    selectedCell = $(this)
    assignment = selectedCell.data("assignment")
    student = selectedCell.parent().children().first().text().trim()
    let cellValue = selectedCell.text().trim()

    // Position the popup near the clicked cell
    $("#popup")
        .fadeIn(200);
        //.css({ top: e.pageY + 10 + "px", left: e.pageX + 10 + "px" })

    // Pre-fill the inputs
    $("#popup-score").val(isNaN(cellValue) ? "" : cellValue);
    $("#popup-comment").val("lookup comment")
        // fetch comment
    var data = {
        request: 'fetch',
        student: student,
        assignment: assignment,
    }
    setTimeout(function() {
        wss_score.send(JSON.stringify(data))
    }, 200)
})

// Save the input values
$(document).on("click", "[id=save-btn]", function () {
    let score = $("#popup-score").val()
    let comment = $("#popup-comment").val()
    let courseid = $("#popup-course_id").val()

    // Update the clicked cell with the new value
    selectedCell.text(score)

    // Hide popup
    $("#popup").fadeOut(200)

    // Send updated data back to the server via WebSocket
    var data = {
        request: 'store',
        student: student,
        assignment: assignment,
        score: score,
        comment: comment,
	courseid: courseid,
    }
    setTimeout(function() {
        wss_score.send(JSON.stringify(data))
    }, 200)
})

// Hide popup when clicking outside
$(document).click(function (event) {
    if (!$(event.target).closest(".popup, td[data-editable='true']").length) {
        $("#popup").fadeOut(200)
    }
})

$(document).ready(function() {
  if (wsURLs.assignment_score) {
    wss_score = new ManagedWebSocket(wsURLs.assignment_score, {
      onMessage: receiveComment,
    })
  } 
})
