// static/js/project_changes.js

$(document).ready(function() {
  if (wsURLs.project_config) {
    wss_projectconfig = new ConfigHandler(wsURLs.project_config, 'configure-project', 'containercard', 'project', 'project_id', ['name', 'image', 'description']);
  } 
})
