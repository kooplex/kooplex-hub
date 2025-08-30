document.addEventListener("DOMContentLoaded", function () {
    let tabs = document.querySelectorAll(".nav-tabs .nav-link")

    // Ensure first active tab starts with text, not an icon
    let firstActiveTab = document.querySelector(".nav-tabs .nav-link.active")
    if (firstActiveTab.dataset.text) {
        firstActiveTab.innerHTML = firstActiveTab.dataset.text
    }

    // Ensure all inactive tabs start with their icons and tooltips
    tabs.forEach(tab => {
        if (!tab.classList.contains("active") && tab.dataset.icon) {
            tab.innerHTML = `<i class="${tab.dataset.icon}" title="${tab.dataset.text}"></i>`
        }
    })

    tabs.forEach(tab => {
        tab.addEventListener("shown.bs.tab", function (event) {
            let previousTab = event.relatedTarget // Previously active tab

            // If there's a previously active tab, swap its text back to an icon with tooltip
            if (previousTab && previousTab.dataset.icon) {
                previousTab.innerHTML = `<i class="${previousTab.dataset.icon}" title="${previousTab.dataset.text}"></i>`
            }

            // Swap the clicked tab's icon with text
            if (this.dataset.text) {
                this.innerHTML = this.dataset.text
            }
        })
    })
})

