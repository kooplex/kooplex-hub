import logging
import json
import threading

from channels.generic.websocket import WebsocketConsumer
from django.utils.html import format_html

from container.models import Container

from container.lib.kubernetes import CE_POOL
from container.forms import FormContainer
from django.template.loader import render_to_string
from .lib import Cluster

logger = logging.getLogger(__name__)


class ContainerConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.accept()
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        assert self.scope['user'].id == self.userid, "not authorized"
        self.lock = threading.Lock()
        self.lut_ev = {}
        self.running = threading.Event()
        self.killed = threading.Event()
        self.t = None
        for c in Container.objects.filter(user__id = self.userid):
            try:
                self.inspect(c.id, CE_POOL.get(c.id, None))
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
                    self.send(text_data=json.dumps({
                        "feedback": f"Container {container.name} finalized its state.", 
                    }))
                    logger.debug(f"Container {container.name} {container.label} finalized its state -> {container.state}")
                    self.inspect(cid, None)
                if not self.lut_ev:
                    self.running.clear()
        logger.info(f"- ws thread for {self.userid}")

    def inspect(self, container_id, event):
        from container.templatetags.container_buttons import container_state, button_start_open, button_stop, button_restart, container_image
        container = self.get_container(container_id)
        resp = { 
            'container-id': container_id,
            'state':  container.state,
            'w_state': container_state(container),
            'w_startopen': button_start_open(container), #FIXME: modal
            'w_stop': button_stop(container),
            'w_restart': button_restart(container),
            'w_image': container_image(container),
        }
        logger.debug(f"{container} --> {resp}")
        self.send(text_data = json.dumps(resp))
        if event is None:
            return
        if event.is_set():
            return

        with self.lock:
            self.lut_ev[event] = container_id
            if not self.running.is_set():
                self.t = threading.Thread(target = self.job)
                self.running.set()
                self.t.start()
        logger.info('new event to inspect')
        self.send(text_data=json.dumps({"feedback": f"Waiting for {container.name} to finalize its state."}))

    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        cid = int(parsed.get('container-id'))
        container = self.get_container(cid)
        command = parsed.get('command')
        if command is None:
            #FIXME: lecsukni a kapcsolatot?
            pass
        elif command == 'configure':
            # request to configure
            self.handle_configuration(container)
        else:
            # request to kube backend
            self.handle_commands(container, command)

    def handle_commands(self, container, command):
        resp = {
            'container-id': container.id,
        }
        if command == 'container-log':
            resp.update( container.check_state(retrieve_log = True) )
            logger.debug(f"fetch {container} -> {resp}")
            self.send(text_data = json.dumps(resp))
        elif command in [ 'start', 'stop', 'restart' ]:
            f = getattr(container, command)
            ev = f()
            self.inspect(container.id, ev)

    def handle_configuration(self, container):
        from django.urls import reverse
        from .lib import Cluster
        from kooplexhub.settings import KOOPLEX
        api = Cluster()
        api.query_nodes_status()

        modal = render_to_string('container_configure.html', { 
            'container': container,
            'wss_monitor': KOOPLEX.get('hub', {}).get('wss_monitor', 'wss://localhost/hub/ws/node_monitor/'),
            'form': FormContainer(initial = { 'user': self.scope['user'] }, instance = container, nodes = list(api.node_df['node'].values)),
        })

        self.send(text_data = json.dumps({
            'configure': 'container', 
            'container-id': container.id,
            'w_modal': modal,
            'action': reverse('container:configure', args = [container.id])
        }))



class MonitorConsumer(WebsocketConsumer):
    def connect(self):
        if self.scope['user'].is_authenticated:
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
            if node:
                api = Cluster()
                api.query_nodes_status(node_list=[node], reset=True)
                api.query_pods_status(field=["spec.nodeName=",node], reset=True)
                api.resources_summary()
                resp.update( api.get_data() )
                resp["feedback"] = f"Node resource information for {node} is updated"
            else:
                node = "default"
                from kooplexhub.settings import KOOPLEX
                kubernetes = KOOPLEX.get('kubernetes',{}).get('resources',{}).get('maxrequests',{})
                resp.update({
                 "feedback" : f"Node resource information for defaults is updated",
                 "avail_cpu": kubernetes.get('cpu',1),
                 "avail_memory": kubernetes.get('memory',2),
                 "avail_gpu": kubernetes.get('nvidia.com/gpu',0),
                    })
            logger.debug(f"fetch {node} -> {resp}")
            self.send(text_data = json.dumps(resp))



