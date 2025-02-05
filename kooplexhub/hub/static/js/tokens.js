$(document).on('click', '[name=test_token]', function() {
    let token=$(this).data('token')
    let tokentype=$(this).data('type')
    if (token===undefined) {
        token=$("input[name=token]").val()
	tokentype=$("select[name=tokentype]").val()
    }
    if (tokentype==="") {
        alert("select tokentype")
	return
    }
    if (token==="") {
        alert("enter a token to test")
	return
    }
  wss_tokens.send(JSON.stringify({
    request: 'test',
    tokentype: tokentype,
    token: token,
  }))
})
$(document).on('click', '[name=save]', function() {
    let token=$("input[name=token]").val()
    let tokentype=$("select[name=tokentype]").val()
    if (tokentype==="") {
        alert("select tokentype")
	return
    }
    if (token==="") {
        alert("enter a token to save")
	return
    }
  wss_tokens.send(JSON.stringify({
    request: 'create',
    tokentype: tokentype,
    token: token,
  }))
})
$(document).on('click', '[name=drop_token]', function() {
    let pk=$(this).data('id')
  wss_tokens.send(JSON.stringify({
    request: 'drop',
    pk: pk,
  }))
})

function token_callback(message) {
    if (message.replace_card) {
        $('[id=tokencard]').replaceWith(message.replace_card)
    }
}

$(document).ready(function() {
  if (wsURLs.tokens) {
        wss_tokens = new ManagedWebSocket(wsURLs.tokens, {
        onMessage: token_callback,
       })
    }
})

