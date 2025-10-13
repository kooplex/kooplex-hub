from django.core.management.base import BaseCommand
from container.models import Image
from hub.models import User
from time import sleep
from test.utils import *
import logging
import random

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test a randomly selected user and it's environment for liveness probe of the image"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Test all images else just one random image")

    def handle(self, *args, **options):
        logger.info(f"TEST: {__name__}")

        u = test_get_test_user()

        if options['all']:
            logger.debug("Testing all images")
            images = list(Image.objects.filter(present=True))
        else:
            images = [random.choice(list(Image.objects.filter(present=True)))]

        succeeded = []
        failed = []

        for selected_image in images:
            logger.debug("Create and launch test container %s", selected_image)

            # Create test environments with the filtered imagetypes
            new_c = test_create_env(user=u, image=selected_image)
            new_c.start()
            sleep(1)

            status = 'starting'
            logger.debug("Waiting for containers to start")
            # check container state every n seconds
            while status != 'running':
                sleep(5)
                logger.debug("Check test container state:")
                    
                if check_container_running(new_c):
                    logger.debug("%s is running", new_c.name)
                    status = 'running'
                else:
                    logger.debug("%s is not running yet", new_c.name)

            # liveness probe
            lp = new_c.image.liveness_probe
            howlongtowait = lp.initial_delay_seconds + lp.timeout_seconds + lp.period_seconds * lp.failure_threshold
            logger.debug(f"Waiting for containers to see if it functions normally. This takes {lp.initial_delay_seconds} + {lp.timeout_seconds} + {lp.period_seconds}*{lp.failure_threshold} = {howlongtowait}.")    
            counter = 0
            while counter < howlongtowait:
                sleep(10)
                counter += 10
                logger.debug(f"{howlongtowait-counter} seconds remaining")

            logger.debug("Check liveness probe")
            if check_container_liveness(new_c):
                logger.debug(f"Liveness probe for {new_c.name} SUCCEEDED")
                status = 'live'
            else:
                logger.debug(f"Liveness probe for {new_c.name} FAILED")
                status = 'failed'
                

            logger.debug("Stop and delete test containers")
            new_c.stop()
            new_c.delete()

        logger.info(f"TEST FINISHED: {__name__}")
        logger.info(f"Succeeded images: {succeeded}")
        logger.info(f"Failed images: {failed}")