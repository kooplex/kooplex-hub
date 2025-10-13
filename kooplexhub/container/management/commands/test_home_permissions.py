# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from test.utils import launch_env, test_create_env, test_get_test_user, check_container_running, \
                        get_container_state
from kubernetes import client, config
from kubernetes.stream import stream

from kooplexhub.settings import KOOPLEX

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test owner permissions for private folders (home ...)."  

    def handle(self, *args, **options):

        testuser = test_get_test_user(username="test1")
        logger.info(f"TEST: {__name__}")
        try:
            # Create a test container for the user
            container = test_create_env(user=testuser)
            logger.debug(f"Container {container.name} created for user {testuser.username}")

            # Launch the environment
            if launch_env(container, stop_after_start=False):
                logger.debug(f"Environment started successfully")
            else:
                logger.error(f"Failed to start environment")

            while  not check_container_running(container):
                time.sleep(2)


            # Find the pod name for the container's user (assuming pod name pattern)
            pod, container_label, namespace = get_container_state(container)
            if not pod:
                logger.error(f"No pod found for user {testuser.username}")
                return

            # # Load kube config
            config.load_kube_config()
            v1 = client.CoreV1Api()
            namespace = KOOPLEX['environmental_variables']['POD_NAMESPACE']

            # Command to execute in the pod
            exec_command = [
                '/bin/sh',
                '-c',
                f'echo "Permissions checked" > /v/{testuser.username}/permissions.txt;',
                f'cat /v/{testuser.username}/permissions.txt;'
            ]
            logger.debug(f"Executing command in pod {pod.metadata.name}: {' '.join(exec_command)}")
            resp = stream(v1.connect_get_namespaced_pod_exec,
                pod.metadata.name,
                namespace,
                command=exec_command,
                container=container_label,
                stderr=True, stdin=False,
                stdout=True, tty=False)            
            logger.debug(f"""Stream: v1.connect_get_namespaced_pod_exec,
                {pod.metadata.name},
                {namespace},
                command={exec_command},
                container={container_label}""")

            logger.debug(f"Command execution response: {resp}")

            # Delete container manually
            container.delete()
            logger.debug(f"Container {container.name} deleted")

        except Exception as e:
            raise e
            print(e)

       logger.info("TEST SUCCESSFULLY FINISHED: %s", __name__)
        
       
