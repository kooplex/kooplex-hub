import logging
import json
import threading

from channels.generic.websocket import WebsocketConsumer

from project.models import UserProjectBinding

logger = logging.getLogger(__name__)


class ProjectConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.accept()
        self.userid = self.scope["url_route"]["kwargs"].get('userid')
        assert self.scope['user'].id == self.userid, "not authorized"

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        command = parsed.get('command')
        pid = int(parsed.get('project-id'))
        resp = {
            'command': command,
            'project-id': pid,
        }
        if command == 'showhide':
            is_hidden = bool(parsed.get('hidden'))
            upb = UserProjectBinding.objects.get(user__id = self.userid, project__id = pid)
            if upb.is_hidden == is_hidden:
                upb.is_hidden ^= True
                upb.save()
            resp['hidden'] = upb.is_hidden
            resp['hidden-count'] = len(UserProjectBinding.objects.filter(user__id = self.userid, is_hidden = True))
            logger.debug(f"showhide {upb} -> {resp}")
            self.send(text_data = json.dumps(resp))
        #elif command in [ 'container-start', 'container-stop', 'container-restart' ]:
        #    c = command.split('-')[-1]
        #    logger.debug(f"{c}...")
        #    f = getattr(container, c)
        #    ev = f()
        #    logger.critical(f"{ev}, {ev.is_set()} {CE_POOL.e}") #FIXME: remove this line
        #    self.inspect(cid, ev)
        #    container = self.get_container(cid)
        #    resp.update({ 'state':  container.state })
        #    logger.debug(f"{c} {container} --> {resp}")
        #    self.send(text_data = json.dumps(resp))


