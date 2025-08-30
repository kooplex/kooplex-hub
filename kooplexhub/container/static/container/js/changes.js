// changes.js

$(document).ready(function() {
  if (wsURLs.container_config) {
    wss_containerconfig = new ConfigHandler(wsURLs.container_config, 'configure-container', 'containercard', 'container', 'container_id', ['name', 'image']);
  } 
})

