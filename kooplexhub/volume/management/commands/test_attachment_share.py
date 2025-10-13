# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from volume.models import Volume, UserVolumeBinding
from test.utils import *

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create an attachment with a user and launch an environment with it. Then check added user's permissions."

    def handle(self, *args, **options):

        testuser = test_get_test_user()
        testuser2 = test_get_test_user()

        logger.info(f"TEST: {__name__}")
        try:
            logger.debug("Creating test attachment")
            folder_name = "test_attachment_share"
            try:
                attachment, uab = test_create_attachment(folder_name=folder_name)
            except:
                logger.debug("Error: Attachment does not exist, creating a new one")

            uab2, created = UserVolumeBinding.objects.get_or_create(user=testuser2, volume=attachment, role=UserVolumeBinding.Role.COLLABORATOR)
            logger.debug(f"shared attachment {attachment.folder} with user {testuser.username}")
            # Create a test environment
            # Mount attachment to environment
            from volume.models import VolumeContainerBinding
            from container.models import Image

            
            container = test_create_env(user=testuser2)
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
           

            while  not check_container_running(container):
                time.sleep(5)

            time.sleep(3)
            logger.debug(f"Container {container.name} is RUNNING")
            # Execute command in the pod to check shared permissions

            # Command to execute in the pod
            exec_command = f"""whoami; ls -l /v/attachments/*; echo Permissions checked by collaborator >> /v/attachments/{attachment.folder}/permissions.txt;
            cat  /v/attachments/{attachment.folder}/permissions.txt"""
            resp = exec_command_in_pod(container, exec_command, user=testuser2)            
            logger.debug(f"Command output: {resp}")
            
        except Exception as e:
            raise e
            print(e)
        finally:
            # Delete container manually
            container.delete()
            logger.debug(f"Container {container.name} deleted")
            # Delete attachment
            # attachment.delete()
            logger.debug(f"Attachment {attachment.folder} deleted")      

        logger.info("TEST SUCCESSFULLY FINISHED: %s", __name__)

