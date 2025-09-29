import logging
import json
import threading

from asgiref.sync import sync_to_async
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from container.conf import CONTAINER_SETTINGS


from hub.util import SyncSkeleton, AsyncSkeleton

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


class ResourceConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        assert request == 'monitor', "wrong request"
        node = parsed.get('node')
        resp = {
            'request': request,
            'node': node,
        }
        if node:
            api = Cluster()
            api.query_nodes_status(node_list=[node], reset=True)
            api.query_pods_status(field=["spec.nodeName=",node], reset=True)
            api.resources_summary()
            resp.update( api.get_data() )
            resp["feedback"] = f"Node resource information for {node} is updated"
        else:
            node = "default"
            r = CONTAINER_SETTINGS['kubernetes']['resources']
            resp.update({
             "feedback" : f"Node resource information for defaults is updated",
             "avail_cpu": r['max_cpu'],
             "avail_memory": r['max_memory'],
             "avail_gpu": r['max_gpu'],
                })
        logger.debug(f"fetch {node} -> {resp}")
        self.send(text_data = json.dumps(resp))
