# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from volume.models import Volume, UserVolumeBinding
from test.utils import launch_env, test_create_attachment, test_create_env

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create and delete an attachment with a user"

    def handle(self, *args, **options):

        logger.debug(f"TEST: {__name__}")
        try:
            folder_name = "test_attachment_share"
            try:
                a, uab = test_create_attachment(folder_name=folder_name)
                logger.error(f"Attachment {a.folder} still exists after deletion")
                a.delete()
                logger.debug(f"Attachment {a.folder} deleted")
            except Volume.DoesNotExist:
                logger.debug(f"Attachment {attachment.folder} successfully deleted")
            
        
            container = test_create_env()
            container.delete()
            logger.debug(f"Container {container.name} deleted")
        except Exception as e:
            raise e
            print(e)
       