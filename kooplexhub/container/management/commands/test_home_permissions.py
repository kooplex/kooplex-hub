# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from test.utils import launch_env, test_create_env, test_get_test_user
from kubernetes import client, config
from kubernetes.stream import stream

from kooplexhub.settings import KOOPLEX

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test owner permissions for private folders (home ...)."  

    def handle(self, *args, **options):

        testuser = test_get_test_user(username="test1")

        logger.debug(f"TEST: {__name__}")
        try:
            # Create a test container for the user
            container = test_create_env(user=testuser)
            logger.debug(f"Container {container.name} created for user {testuser.username}")

            # Launch the environment
            if launch_env(container, stop_after_start=False):
                logger.debug(f"Environment started successfully")
            else:
                logger.error(f"Failed to start environment")
            # Load kube config
            config.load_kube_config()

            # Find the pod name for the container's user (assuming pod name pattern)
            pod_label_selector = f"user={testuser.username}"
            v1 = client.CoreV1Api()
            namespace=KOOPLEX.get('kubernetes',{}).get('namespace', "default")
            pods = v1.list_namespaced_pod(namespace=namespace, 
            label_selector=pod_label_selector)
            if not pods.items:
                logger.error(f"No pod found for user {testuser.username}")
                return

            pod_name = pods.items[0].metadata.name
            container_name = pods.items[0].spec.containers[0].name

            # Command to execute in the pod
            exec_command = [
                '/bin/sh',
                '-c',
                f'echo "Permissions checked" > /v/{testuser.username}/permissions.txt;',
                f'cat /v/{testuser.username}/permissions.txt;'
            ]

            resp = stream(v1.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                command=exec_command,
                container=container_name,
                stderr=True, stdin=False,
                stdout=True, tty=False)
            
            logger.debug(f"Command output: {resp}")

            # Delete container manually
            container.delete()
            logger.debug(f"Container {container.name} deleted")

        except Exception as e:
            raise e
            print(e)
       