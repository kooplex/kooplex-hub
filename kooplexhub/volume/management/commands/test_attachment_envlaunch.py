# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from volume.models import Volume, UserVolumeBinding
from test.utils import launch_env, test_create_attachment

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create an attachment with a user and launch an environment with it."

    def handle(self, *args, **options):

        logger.debug(f"TEST: {__name__}")
        try:
            logger.debug("Creating test attachment")
            folder_name = "test_attachment_share"
            attachment, uab = test_create_attachment(folder_name=folder_name)
            logger.debug(f"Created attachment {attachment.folder} with user {uab.user.username}")
            # Create a test environment
            # Mount attachment to environment
            from volume.models import VolumeContainerBinding
            from container.models import Image

            # Get the first available image
            image = Image.objects.filter(present=True).first()
            if not image:
                raise ValueError("No present images found") 

            # Create a test container for the user
            container = test_create_env(user=uab.user, image=image)
            logger.debug(f"Container {container.name} created for user {uab.user.username}")

            # Bind the attachment (volume) to the container
            vcb = VolumeContainerBinding(volume=attachment, container=container)
            vcb.save()
            logger.debug(f"VolumeContainerBinding created for attachment {attachment.folder} and container {container.name}")

            # Launch the environment
            if launch_env(container):
                logger.debug(f"Environment for attachment {attachment.folder} started successfully")
            else:
                logger.error(f"Failed to start environment for attachment {attachment.folder}")
            # Delete the attachment
            logger.debug(f"Deleting attachment {attachment.folder}")
            attachment.delete()
            logger.debug(f"Attachment {attachment.folder} deleted")
            # Check if the attachment is deleted
            try:
                a = Volume.objects.get(folder=attachment.folder)
                logger.error(f"Attachment {a.folder} still exists after deletion")
            except Volume.DoesNotExist:
                logger.debug(f"Attachment {attachment.folder} successfully deleted")
            
        except Exception as e:
            raise e
            print(e)
       