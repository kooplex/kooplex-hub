let showTimer, hideTimer;

$(document).on("mouseenter", ".hover-dropdown", function () {
    let dropdown = $(this).find(".dropdown-content");

    clearTimeout(hideTimer);  // Prevent hiding if hovering back
    showTimer = setTimeout(() => {
        dropdown.fadeIn(200);  // Show after 0.2s
    }, 200);
});

$(document).on("mouseleave", ".hover-dropdown", function () {
    let dropdown = $(this).find(".dropdown-content");

    clearTimeout(showTimer);  // Prevent showing if quickly leaving
    hideTimer = setTimeout(() => {
        dropdown.fadeOut(200);  // Hide after 1s
    }, 1000);
});

// Ensure the dropdown remains open when hovering inside it
$(document).on("mouseenter", ".dropdown-content", function () {
    clearTimeout(hideTimer);
});

$(document).on("mouseleave", ".dropdown-content", function () {
    hideTimer = setTimeout(() => {
        $(this).fadeOut(200);  // Hide after 1s when pointer leaves
    }, 1000);
});

