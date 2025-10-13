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
    help = "Delete test created attachments and its' bindings"

    def handle(self, *args, **options):

        logger.info(f"TEST: {__name__}")
        try:
            # Search for test attachments and delete them
            attachments = Volume.objects.filter(folder__startswith="test_")
            for attachment in attachments:
                attachment.delete()
                logger.debug(f"Attachment {attachment.folder} deleted")
            
        except Exception as e:
            raise e
            print(e)

        logger.info("TEST CLEANUP SUCCESSFULLY FINISHED: %s", __name__)
    
       