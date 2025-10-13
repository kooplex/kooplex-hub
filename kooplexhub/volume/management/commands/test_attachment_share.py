# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from volume.models import Volume, UserVolumeBinding
from test.utils import launch_env, test_create_attachment, test_create_env, test_get_test_user
from kubernetes import client, config
from kubernetes.stream import stream

from kooplexhub.settings import KOOPLEX


logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create an attachment with a user and launch an environment with it. Then check added user's permissions."

    def handle(self, *args, **options):

        testuser = test_get_test_user(username="test1")

        logger.debug(f"TEST: {__name__}")
        try:
            logger.debug("Creating test attachment")
            folder_name = "test_attachment_share"
            try:
                attachment = Volume.objects.get(folder=folder_name)
            except Volume.DoesNotExist:
                logger.debug("Error: Attachment does not exist, creating a new one")

            uab, created = UserVolumeBinding.objects.get_or_create(user=testuser, volume=attachment, role=UserVolumeBinding.RL_COLLABORATOR)
            logger.debug(f"shared attachment {attachment.folder} with user {testuser.username}")
            # Create a test environment
            # Mount attachment to environment
            from volume.models import VolumeContainerBinding
            from container.models import Image

            
            container = test_create_env(user=testuser)
            logger.debug(f"Container {container.name} created for user {testuser.username}")

            # Bind the attachment (volume) to the container
            vcb, exists = VolumeContainerBinding.objects.get_or_create(volume=attachment, container=container)
            if exists:
                logger.debug(f"VolumeContainerBinding already exists for attachment {attachment.folder} and container {container.name}")
            else:
                logger.debug(f"Creating VolumeContainerBinding for attachment {attachment.folder} and container {container.name}")
                vcb.save()    

            # Launch the environment
            if launch_env(container, stop_after_start=False):
                logger.debug(f"Environment for attachment {attachment.folder} started successfully")
            else:
                logger.error(f"Failed to start environment for attachment {attachment.folder}")
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
                'ls -l /v/attachments/;' #+ attachment.folder
                f'echo "Permissions checked by collaborator" >> /v/attachments/{attachment.folder}/permissions.txt'
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
       