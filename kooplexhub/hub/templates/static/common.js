// my boolean converter
function B(x) {
  if (typeof x === 'boolean') {
    return x;
  }
  if (typeof x === 'string') {
    return Boolean(x == 'true') || Boolean(x == 'True');
  }
  console.log("fallback to unhandled type");
  return Boolean(x);
};

// on load feedback messages panel is empty, hide it
$(document).ready(function () {
  var widget = $("#feedbackMessages");
  widget.hide();
});

// display some feedback messages
function feedback(msg) {
  var widget = $("#feedbackMessages");
  widget.show();
  $("#feedbackContent").append("<p>" + msg + "</p>");
  setTimeout(function () { widget.hide() }, 10000);
	// TODO: too many paragraphs, clear oldest
}


// open a websocket
function open_ws(url, callback, onclose) {
  console.log('open socket:', url);
  const socket = new WebSocket(url);
  socket.onclose = function(e) {
    console.error('Socket closed unexpectedly');
    if (onclose) {
      onclose(e);
    }
  };
  socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data['feedback']) {
      feedback(data['feedback']);
    }
    callback(data);
  }
  return socket;
};