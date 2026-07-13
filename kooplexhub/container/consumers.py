import logging
import json

from asgiref.sync import sync_to_async

from container.models import Container

from channels.generic.websocket import AsyncJsonWebsocketConsumer

#from .lib import Cluster

from .tasks import *

from hub.util import SyncSkeleton, AsyncSkeleton

from .conf import CONTAINER_SETTINGS

logger = logging.getLogger(__name__)



class CSyncSkeleton(SyncSkeleton):
    def get_container(self, container_id):
        return Container.objects.get(id = container_id, user__id = self.userid)

class ContainerFetchlogConsumer(CSyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        cid = int(parsed.get('pk'))
        container = self.get_container(cid)
        request = parsed.get('request')
        assert request == 'container-log', "wrong request"
        resp = container.retrieve_log()
        logger.debug(f"fetch {container} -> {resp[:10]}...")
        self.send(text_data = json.dumps({ 'podlog': resp}))


class ContainerControlConsumer(AsyncSkeleton):
    identifier_='container-{user.id}'
    def get_container(self, container_id):
        return sync_to_async(Container.objects.get)(id = container_id, user__id = self.userid)

    async def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        cid = int(parsed.get('pk'))
        container = await self.get_container(cid)
        request = parsed.get('request')
        if request == 'start':
            await self.send(text_data=json.dumps({"feedback": f'Starting container {container.name}. Keep calm until its state is finalized.' }))
            await sync_to_async(container.start)()
        elif request == 'stop':
            await self.send(text_data=json.dumps({"feedback": f'Stopping container {container.name}.' }))
            await sync_to_async(container.stop)()
        elif request == 'restart':
            await self.send(text_data=json.dumps({"feedback": f'Restarting container {container.name}' }))
            await sync_to_async(container.restart)()
        else:
            logger.error(f'wrong ws call request: {request}')



class ContainerLiveConsumer(AsyncJsonWebsocketConsumer):
    """
    Live invalidation feed for container/environment pages.

    This consumer does not perform mutations.
    It only receives server-side live events and forwards them to browsers.
    """

    async def connect(self):
        user = self.scope.get("user")

        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user = user
        self.user_group_name = self.group_name_for_user(user.pk)

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name,
            )

    @staticmethod
    def group_name_for_user(user_id):
        return f"container-live-user-{user_id}"

    async def receive_json(self, content, **kwargs):
        """
        Browser-to-server messages are intentionally ignored for now.

        Later this could accept pings, client_id registration, etc.
        """
        return

    async def container_live_event(self, event):
        """
        Handler for channel layer events.

        group_send must use:
            {"type": "container.live_event", "payload": {...}}

        Channels maps "container.live_event" -> container_live_event().
        """
        await self.send_json(event["payload"])

    @staticmethod
    def group_name_for_user(user_id):
        return f"container-live-user-{user_id}"





#class MonitorConsumer(SyncSkeleton):
#    def receive(self, text_data):
#        parsed = json.loads(text_data)
#        logger.debug(parsed)
#        request = parsed.get('request')
#        assert request == 'monitor-node', "wrong request"
#        node = parsed.get('node')
#        resp = {
#            'request': request,
#            'node': node,
#        }
#        if node:
#            api = Cluster()
#            api.query_nodes_status(node_list=[node], reset=True)
#            api.query_pods_status(field=["spec.nodeName=",node], reset=True)
#            api.resources_summary()
#            resp.update( api.get_data() )
#            resp["feedback"] = f"Node resource information for {node} is updated"
#        else:
#            node = "default"
#            resp.update({
#             "feedback" : f"Node resource information for defaults is updated",
#             "avail_cpu": CONTAINER_SETTINGS['kubernetes']['resources']['max_cpu'],
#             "avail_memory": CONTAINER_SETTINGS['kubernetes']['resources']['max_memory'],
#             "avail_gpu": CONTAINER_SETTINGS['kubernetes']['resources']['max_gpu'],
#                })
#        logger.debug(f"fetch {node} -> {resp}")
#        self.send(text_data = json.dumps(resp))



