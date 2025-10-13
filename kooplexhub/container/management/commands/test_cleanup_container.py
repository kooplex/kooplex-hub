# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from container.models import *
import time
import logging

from volume.models import Volume, UserVolumeBinding
from test.utils import launch_env, test_create_attachment, test_create_env

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Cleanup test created environments and containers"

    def handle(self, *args, **options):

        logger.info(f"TEST: {__name__}")
        try:
            # Search for test environments and delete them
            
            envs = Container.objects.filter(name__startswith="test")
            for env in envs:
                env.delete()
                logger.debug(f"Environment {env.name} deleted")
        except Exception as e:
            raise e
            print(e)

        logger.info("TEST CLEANUP SUCCESSFULLY FINISHED: %s", __name__)
    
       