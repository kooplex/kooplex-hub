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


// search objects by userinput
//FIXME: when typing very fast we may sleep a while
$("input[id^=search_]").keyup(function() {
  var obj = $( this ).attr("id").split("_", 2)[1];
  var pattern = $( this ).val().toUpperCase();
  // console.log( "search", obj, ":", pattern );
  $("input[id^=" + obj + "-search-]").each(function() {
    var obj_id = $( this ).attr("id").split("-", 3)[2];
    var str = $( this ).val();
    var match = $( "#" + obj + "-match-" + obj_id );
    is_found = true;
    if (pattern.length > 0) {
      is_found = str.indexOf(pattern) > -1;
    }
    match.val( is_found );
    if (typeof is_visible_callback === "function") {
      show_object = is_visible_callback(obj, obj_id, pattern.length == 0, is_found);
    } else {
      show_object = is_found;
    }
    $("#" + obj + "-isshown-" + obj_id).val(show_object);
  });
  set_visibility(obj);
});

// set visibility states for objects: cards, table rows
function set_visibility(obj) {
  found = false;
  $("div[id^=hideable-" + obj + "-]").each(function() {
    found = true;
    obj_id = $( this ).attr("id").split("-", 3)[2];
    show_object = B($("#" + obj + "-isshown-" + obj_id).val());
    if (show_object) {
      $( this ).show();
    } else {
      $( this ).hide();
    }
  });
  // fall back to manipulate a table rows, tr expected 2 levels up
  if (! found) {
    $("input[id^=" + obj + "-isshown-]").each(function() {
      w = $(this).parent().parent();
      show = B($(this).val());
      if ( show ) {
        //w.show();
        w.removeClass('d-none');
      } else {
        //w.hide();
        w.addClass('d-none');
      }
    });
  }
};
