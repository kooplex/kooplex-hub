# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging
from volume.conf import VOLUME_SETTINGS

from volume.models import Volume, UserVolumeBinding
from test.utils import *

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create an attachment with a user, mount it and launch an environment with it. Then check owner permissions."  

    def handle(self, *args, **options):

        logger.info(f"TEST: {__name__}")
        try:
            logger.debug("Creating test attachment")
            folder_name = "test_attachment_ownerp"
            attachment, uab = test_create_attachment(folder_name=folder_name)
            user = uab.user
            logger.debug(f"Created attachment {attachment.folder} with user {uab.user.username}")
            # Create a test environment
            # Mount attachment to environment
            from container.models import Container
            from volume.models import VolumeContainerBinding
            from container.models import Image



            # Create a test container for the user
            container = test_create_env(user=user)
            logger.debug(f"Container {container.name} created for user {user.username}")

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


            # Checko pod state
            while not check_container_running(container):
                logger.debug(f"Container {container.name} is NOT RUNNING")
                time.sleep(5)

            # Execute command in the pod to check permissions
            folder = VOLUME_SETTINGS['mounts']['attachment']['mountpoint'].format(volume=attachment)
            exec_command = f"whoami; ls -l /v/attachments/; echo $HOME Permissions checked > {folder}/permissions.txt; cat {folder}/permissions.txt"
            resp = exec_command_in_pod(container, exec_command, user)
            logger.debug(f"Command output: {resp}")

        except Exception as e:
            raise e
            print(e)
        finally:
            # Cleanup
            container.delete()
            logger.debug(f"Container {container.name} deleted in cleanup")
            # attachment.delete()
            logger.debug(f"Attachment {attachment.folder} deleted in cleanup")
            
        logger.info("TEST SUCCESSFULLY FINISHED: %s", __name__)
