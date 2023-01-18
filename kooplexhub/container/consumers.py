import logging
import json
import threading

from channels.generic.websocket import WebsocketConsumer

from container.models import Container

from container.lib.kubernetes import CE_POOL
from .lib import Cluster

logger = logging.getLogger(__name__)


class ContainerConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        self.userid = self.scope["url_route"]["kwargs"].get('userid')
        self.lock = threading.Lock()
        self.lut_ev = {}
        self.running = threading.Event()
        self.killed = threading.Event()
        self.t = None
        for c in Container.objects.filter(user__id = self.userid, state__in = [ Container.ST_STARTING, Container.ST_STOPPING ]):
            try:
                self.inspect(c.id, CE_POOL.get(c.id))
            except:
                pass

    def disconnect(self, close_code):
        self.killed.set()

    def get_container(self, container_id):
        return Container.objects.get(id = container_id, user__id = self.userid)

    def job(self):
        logger.critical('START')
        logger.info(f"+ ws thread for {self.userid}")
        while self.running.is_set():
            with self.lock:
                ev = next(iter(self.lut_ev))
            ev.wait(1)
            with self.lock:
                completed = []
                for e in self.lut_ev.keys():
                    if e.is_set():
                        completed.append(e)
                for e in completed:
                    cid = self.lut_ev.pop(e)
                    container = self.get_container(cid)
                    self.send(text_data=json.dumps({"command": "feedback", "message": f"Container {container.friendly_name} finalized its state.", "container-id": cid, "state": container.state}))
                    logger.debug(f"Container {container.friendly_name} finalized its state -> {container.state}")
                if not self.lut_ev:
                    self.running.clear()
        logger.info(f"- ws thread for {self.userid}")

    def inspect(self, container_id, event):
        if event.is_set():
            return
        with self.lock:
            self.lut_ev[event] = container_id
            if not self.running.is_set():
                self.t = threading.Thread(target = self.job)
                self.running.set()
                self.t.start()
        logger.info('new event to inspect')
        #container = self.get_container(container_id)
        #self.send(text_data=json.dumps({"command": "feedback", "message": f"Waiting for {container.friendly_name} to finalize its state."}))

    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        command = parsed.get('command')
        cid = int(parsed.get('container-id'))
        container = self.get_container(cid)
        resp = {
            'command': command,
            'container-id': cid,
        }
        if command == 'container-log':
            resp.update( container.check_state(retrieve_log = True) )
            logger.debug(f"fetch {container} -> {resp}")
            self.send(text_data = json.dumps(resp))
        elif command in [ 'container-start', 'container-stop', 'container-restart' ]:
            c = command.split('-')[-1]
            logger.debug(f"{c}...")
            f = getattr(container, c)
            ev = f()
            logger.critical(f"{ev}, {ev.is_set()} {CE_POOL.e}") #FIXME: remove this line
            self.inspect(cid, ev)
            container = self.get_container(cid)
            resp.update({ 'state':  container.state })
            logger.debug(f"{c} {container} --> {resp}")
            self.send(text_data = json.dumps(resp))


class MonitorConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        command = parsed.get('command')
        resp = {
            'command': command,
        }
        if command == 'monitor-node':
            node = parsed.get('node')
            resp['node'] = node
            api = Cluster(node)
            api.resources_summary()
            resp.update( api.get_data() )
            logger.debug(f"fetch {node} -> {resp}")
            self.send(text_data = json.dumps(resp))



