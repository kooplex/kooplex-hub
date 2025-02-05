import logging
import json
import threading

from asgiref.sync import sync_to_async
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string



from hub.util import is_model_field, SyncSkeleton, AsyncSkeleton

logger = logging.getLogger(__name__)

 

class TokenConfigurator(SyncSkeleton):
    def receive(self, text_data):
        #FIXME: ez nem pluginszerű így
        from .models import Token, TokenType
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        assert request in [ 'drop', 'create', 'test' ]
        if request=='create':
            tt=parsed.get('tokentype')
            token=parsed.get('token')
            Token.objects.create(user_id=self.userid, value=token, type=TokenType.objects.get(name=tt))
            msg="Token created"
        elif request=='drop':
            pk=parsed.get('pk')
            Token.objects.filter(user__id=self.userid, id=pk).delete()
            msg="Token deleted"
        elif request=='test':
            tt=parsed.get('tokentype')
            token=parsed.get('token')
            if tt=='Canvas':
                from canvas.canvasapi import CanvasAPI
                t=Token(value=token, type=TokenType.objects.get(name=tt))
                api=CanvasAPI(t)
                msg=str(api.check_connection())
            else:
                msg="FIXME THIS IS NOT IMPLEMENTED YET"
        user_tokens=Token.objects.filter(user__id=self.userid)
        tokentypes=TokenType.objects.all().exclude(id__in=[ t.type.id for t in user_tokens])
        self.send(text_data = json.dumps({
            "feedback": msg,
            "replace_card": render_to_string("widgets/card_tokens.html", {'tokens': user_tokens, 'tokentypes':tokentypes}),
            }))



