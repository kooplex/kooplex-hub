import logging
import time
from kubernetes import client, config, watch
from django.db import connection, connections, close_old_connections
from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from container.models import Container

from django.utils import timezone
from ...conf import CONTAINER_SETTINGS

from container.templatetags.container_buttons import (
        button_start, button_stop,
        button_open, button_restart,
        button_fetchlogs, indicator_state
    )

logger = logging.getLogger(__name__)

def _replace_widgets(container):
    return {
        f'[data-action=start][data-pk={container.id}]': button_start.render(container),
        f'[data-action=stop][data-pk={container.id}]': button_stop.render(container),
        f'[name=opencontainer][data-id={container.id}]': button_open.render(container),
        f'[name=fetch][data-id={container.id}]': button_fetchlogs.render(container),
        f'[name=phase][data-id={container.id}]': indicator_state.render(container),
        f'[data-action=restart][data-pk={container.id}]': button_restart.render(container),
        }

state_mapper = {
    'Running': Container.State.RUNNING,
    'Not Found': Container.State.NOTPRESENT,
    'Killing': Container.State.STOPPING,
    'Pending': Container.State.STARTING,
#    'Scheduled': Container.State.STARTING,
#    'Pulling': Container.State.STARTING,
#    'BackOff': Container.State.STARTING,
#    'Pulled': Container.State.STARTING,
#    'Created': Container.State.STARTING,
#    'SandboxChanged': Container.State.STARTING,
#    'Started': Container.State.RUNNING,
#    'Not present': Container.State.NOTPRESENT,
#    'FailedCreatePodSandBox': Container.State.ERROR,
#    'FailedMount': Container.State.ERROR,
#    'FailedKillPod': Container.State.STOPPING,
#
#
#    'FailedToUpdateEndpoint': Container.State.NOTPRESENT, #FIXME: is it complete? possible keys: 'CreateContainerConfigError', 'ImagePullBackOff'
}


class Command(BaseCommand):
    help = "Start Kubernetes Pod Watcher"

    from kubernetes import client, config, watch

    def parse_pod_event(self, event):
        pod = event["object"]
        event_type = event["type"]
        pod_name = pod.metadata.name
        phase = pod.status.phase
        reason = pod.status.reason
        print(f"\n🔹 Event: {event_type} | Pod: {pod_name} | Phase: {phase} | Reason {reason}")

        # Is the pod evicted?
        if reason == "Evicted":
            print ("JAJJ")
    
        # Print pod conditions
        if pod.status.conditions:
            for condition in pod.status.conditions:
                print(f"  - Condition: {condition.type}, Status: {condition.status}, Reason: {condition.reason}")
    
        # Print container states
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                container_name = container_status.name
                state = container_status.state
                print(f"  🏗️ Container: {container_name}")
                if state.waiting:
                    print(f"    ⏳ Waiting: {state.waiting.reason}")
                if state.running:
                    print(f"    ✅ Running since {state.running.started_at}")
                if state.terminated:
                    print(f"    ❌ Terminated: {state.terminated.reason}, Exit Code: {state.terminated.exit_code}")

        if event_type == 'ADDED':
            return phase

        if pod.metadata.deletion_timestamp:
            if event_type == 'MODIFIED':
                return "Killing"
            elif event_type == 'DELETED':
                return "Not Found"

        last_condition=pod.status.conditions[0]
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                if pod_name != container_status.name:
                    continue # skip sidecar checking
                state = container_status.state
                if state.waiting:
                    return state.waiting.reason
                if state.running:
                    return 'Running'
                if state.terminated:
                    return state.terminated.reason
        else:
            return last_condition.type


    def feedback(self,container, message):
        channel_layer=get_channel_layer()
        async_to_sync(channel_layer.group_send)(f"container-{container.user.id}", {
              "type": "feedback",
              "feedback": message,
              "container_id": container.id,
              "replace_widgets": _replace_widgets(container),
          })


    def handle(self, *args, **options):
        print("Starting Kubernetes Pod Watcher...")
        v1 = client.CoreV1Api()
        namespace = CONTAINER_SETTINGS['kubernetes']['namespace']

        # Load Kubernetes configuration
        try:
            config.load_kube_config()  # Use config.load_incluster_config() in Kubernetes
        except Exception as e:
            self.stderr.write(f"Error loading K8s config: {e}")
            return

        containers = { c.label: (c.id, c.state, c.state_backend) for c in Container.objects.all() }
        # first test for missing containers:
        for label, (container_id, _, _) in containers.items():
            try:
                v1.read_namespaced_pod_status(namespace = namespace, name = label)
            except client.rest.ApiException as e:
                if e.reason == 'Not Found':
                    container=Container.objects.get(id=container_id)
                    feedback=container.state!=container.State.NOTPRESENT
                    container.state=container.State.NOTPRESENT
                    container.state_backend=e.reason
                    container.state_lastcheck_at = timezone.now()
                    container.save()
                    if feedback:
                        self.feedback(container, f'Container {container.name} is not present any more')
                else:
                    logger.error(f'Unhandled error pod label: {label} -- {e}')

        w = watch.Watch()

        while True:
            try:
                print("🔍 Watching for pod events...")
                for event in w.stream(v1.list_namespaced_pod, namespace=namespace):
                    close_old_connections()  # Close any stale DB connections
                    connection.ensure_connection()
                    backend_state=self.parse_pod_event(event)
                    pod = event["object"]
                    pod_name = pod.metadata.name
                    if not pod_name in containers:
                        c_new=Container.objects.filter(label=pod_name).first()
                        if c_new:
                            containers[pod_name]=(c_new.id, c_new.state, c_new.state_backend)
                            logger.info(f"A new container cached {pod_name}")
                        else:
                            logger.warning(f"Most probably {pod_name} is a dangling container. Consider removing")
                            continue
                    container_id, state_old, state_backend_old = containers.get(pod_name)
                    state_new=state_mapper.get(backend_state)
                    changed=(state_backend_old != backend_state) or (state_new and (state_old != state_new))
                    _chg="state change" if changed else "state remains"
                    logger.debug (f"{pod_name} {_chg}: backend {state_backend_old} -> {backend_state} | model {state_old} -> {state_new}")
                    if changed:
                        container=Container.objects.filter(id=container_id).first()
                        if not container:
                            print(f"⚠️  container {pod_name} disappeared")
                            if pod_name in containers:
                                containers.pop(pod_name)
                                logger.info(f"A container {pod_name} removed from cache")
                            continue
                        container.state_backend=backend_state
                        if state_new:
                            container.state=state_new
                        container.state_lastcheck_at = timezone.now()
                        container.save()
                        self.feedback(container, f'Container {container.name} changed its state: {backend_state}({state_new}).')
                        containers[pod_name]=(container.id, container.state, container.state_backend)
                        if state_new==container.State.NOTPRESENT and container.require_running:
                            container.start()
                        elif state_new==container.State.RUNNING:
                            container.addroutes()
            except Exception as e:
                print(f"⚠️ Error in watcher: {e}")
                connections.close_all()
                logger.error(f"⚠️ Error in watcher -- {e}")
                print("Restarting watcher in 5 seconds...")
                time.sleep(5)
                continue



