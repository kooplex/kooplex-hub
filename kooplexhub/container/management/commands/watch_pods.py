import logging
import time
from tqdm import tqdm

from kubernetes import client, config, watch

from django.db import connection, connections, close_old_connections
from django.core.management.base import BaseCommand
from django.utils import timezone

from container.models import Container
from container.services.live import broadcast_container_runtime_changed
from ...conf import CONTAINER_SETTINGS


logger = logging.getLogger(__name__)


state_mapper = {
    "Running": Container.State.RUNNING,
    "Not Found": Container.State.NOTPRESENT,
    "Killing": Container.State.STOPPING,
    "Pending": Container.State.STARTING,

    "ContainerCreating": Container.State.STARTING,
    "PodInitializing": Container.State.STARTING,
    "Scheduled": Container.State.STARTING,
    "Pulling": Container.State.STARTING,
    "Pulled": Container.State.STARTING,
    "Created": Container.State.STARTING,
    "Started": Container.State.RUNNING,

    "ErrImagePull": Container.State.ERROR,
    "ImagePullBackOff": Container.State.ERROR,
    "CreateContainerConfigError": Container.State.ERROR,
    "CrashLoopBackOff": Container.State.ERROR,
    "Failed": Container.State.ERROR,
    "FailedMount": Container.State.ERROR,
    "FailedCreatePodSandBox": Container.State.ERROR,

    "Completed": Container.State.NOTPRESENT,
    "Succeeded": Container.State.NOTPRESENT,
}



class Command(BaseCommand):
    help = "Start Kubernetes Pod Watcher"

    from kubernetes import client, config, watch

    def parse_pod_event(self, event):
        pod = event["object"]
        event_type = event["type"]
        pod_name = pod.metadata.name
        node_name = pod.spec.node_name
        phase = pod.status.phase
        reason = pod.status.reason
        print(f"\n🔹 Event: {event_type} | Pod: {pod_name} @ {node_name} | Phase: {phase} | Reason {reason}")

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

        if pod.metadata.deletion_timestamp:
            if event_type == 'MODIFIED':
                return "Killing", node_name
            elif event_type == 'DELETED':
                return "Not Found", None

        if pod.status.conditions:
            last_condition = pod.status.conditions[0]
        else:
            last_condition = None
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                if pod_name != container_status.name:
                    continue # skip sidecar checking
                state = container_status.state
                if state.waiting:
                    return state.waiting.reason, node_name
                if state.running:
                    return 'Running', node_name
                if state.terminated:
                    return state.terminated.reason, node_name
        else:
            if last_condition:
                return last_condition.type, node_name
        
        return phase, node_name


    def feedback(self, container, message, backend_state=None):
        logger.info(message)
    
        broadcast_container_runtime_changed(
            container=container,
            reason=message,
            backend_state=backend_state,
        )



    def handle(self, *args, **options):
        print("Starting Kubernetes Pod Watcher...")
        v1 = client.CoreV1Api()
        namespace = CONTAINER_SETTINGS.kubernetes.namespace

        # Load Kubernetes configuration
        try:
            config.load_kube_config()  # Use config.load_incluster_config() in Kubernetes
        except Exception as e:
            self.stderr.write(f"Error loading K8s config: {e}")
            return

        containers = {
            c.label: (c.id, c.state, c.state_backend)
            for c in Container.objects.all()
        }
        
        for label, (container_id, _, _) in tqdm(containers.items()):
            try:
                v1.read_namespaced_pod_status(
                    namespace=namespace,
                    name=label,
                )
        
            except client.rest.ApiException as e:
                if e.reason == "Not Found":
                    container = Container.objects.get(id=container_id)
                    changed = container.state != container.State.NOTPRESENT
        
                    container.state = container.State.NOTPRESENT
                    container.state_backend = e.reason
                    container.state_lastcheck_at = timezone.now()
                    container.runtime_node = None
                    container.cpuusage = None
                    container.memoryusage = None
                    container.idle = None
        
                    container.save(
                        update_fields=[
                            "state",
                            "state_backend",
                            "state_lastcheck_at",
                            "runtime_node",
                            "cpuusage",
                            "memoryusage",
                            "idle",
                        ]
                    )
        
                    containers[label] = (
                        container.id,
                        container.state,
                        container.state_backend,
                    )
        
                    if changed:
                        self.feedback(
                            container,
                            f"Container {container.name} is not present any more.",
                            backend_state=e.reason,
                        )
        
                    if container.require_running:
                        container.start()
                        self.feedback(
                            container,
                            f"Container {container.name} was requested to restart because it is required to run.",
                            backend_state=e.reason,
                        )
        
                else:
                    logger.error(f"Unhandled error pod label: {label} -- {e}")

        w = watch.Watch()

        while True:
            try:
                print("🔍 Watching for pod events...")
                for event in w.stream(v1.list_namespaced_pod, namespace=namespace):
                    close_old_connections()
                    connection.ensure_connection()
                
                    backend_state, node_name = self.parse_pod_event(event)
                
                    pod = event["object"]
                    pod_name = pod.metadata.name
                
                    if pod_name not in containers:
                        c_new = Container.objects.filter(label=pod_name).first()
                
                        if c_new:
                            containers[pod_name] = (
                                c_new.id,
                                c_new.state,
                                c_new.state_backend,
                            )
                            logger.info(f"A new container cached {pod_name}")
                        else:
                            logger.warning(
                                f"Most probably {pod_name} is a dangling container. Consider removing"
                            )
                            continue
                
                    container_id, state_old, state_backend_old = containers.get(pod_name)
                
                    state_new = state_mapper.get(backend_state)
                
                    changed = (
                        state_backend_old != backend_state
                        or (
                            state_new
                            and state_old != state_new
                        )
                    )
                
                    change_label = "state change" if changed else "state remains"
                
                    logger.debug(
                        f"{pod_name} {change_label}: "
                        f"backend {state_backend_old} -> {backend_state} | "
                        f"model {state_old} -> {state_new}"
                    )
                
                    if not changed:
                        continue
                
                    container = (
                        Container.objects
                        .filter(id=container_id)
                        .select_related("user")
                        .first()
                    )
                
                    if not container:
                        print(f"⚠️  container {pod_name} disappeared")
                
                        if pod_name in containers:
                            containers.pop(pod_name)
                            logger.info(f"A container {pod_name} removed from cache")
                
                        continue
                
                    container.state_backend = backend_state
                    container.runtime_node = node_name
                    container.state_lastcheck_at = timezone.now()
                
                    update_fields = [
                        "state_backend",
                        "runtime_node",
                        "state_lastcheck_at",
                    ]
                
                    if state_new:
                        container.state = state_new
                        update_fields.append("state")
                
                    if state_new == Container.State.RUNNING:
                        if not container.launched_at:
                            container.launched_at = timezone.now()
                            update_fields.append("launched_at")
                
                    if state_new == Container.State.NOTPRESENT:
                        container.cpuusage = None
                        container.memoryusage = None
                        container.idle = None
                        container.runtime_node= None
                
                        update_fields.extend(
                            [
                                "cpuusage",
                                "memoryusage",
                                "idle",
                                "runtime_node",
                            ]
                        )
                
                    container.save(update_fields=list(dict.fromkeys(update_fields)))
                
                    containers[pod_name] = (
                        container.id,
                        container.state,
                        container.state_backend,
                    )
                
                    if state_new == Container.State.NOTPRESENT and container.require_running:
                        container.start()
                
                    elif state_new == Container.State.RUNNING:
                        container.addroutes()
                
                    self.feedback(
                        container,
                        f"Container {container.name} changed its state: {backend_state} ({state_new}).",
                        backend_state=backend_state,
                    )

            except Exception as e:
                print(f"⚠️ Error in watcher: {e}")
                connections.close_all()
                logger.error(f"⚠️ Error in watcher -- {e}")
                print("Restarting watcher in 5 seconds...")
                time.sleep(5)
                continue



