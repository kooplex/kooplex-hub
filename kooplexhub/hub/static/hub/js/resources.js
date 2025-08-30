function resources_callback(message) {
    if (message.replace_card) {
        $('[id=resources]').replaceWith(message.replace_card)
    }
}

$(document).ready(function() {
    if (wsURLs.resources) {
          wss_resources = new ManagedWebSocket(wsURLs.resources, {
          onMessage: resources_callback,
         })
      }
  })