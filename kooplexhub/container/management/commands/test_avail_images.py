from django.core.management.base import BaseCommand
from container.models import Image
from hub.models import User
from time import sleep
from test.utils import *
import logging

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test available images by creating, starting, and stopping containers in parallel"

    def handle(self, *args, **options):
        logger.info(f"TEST: {__name__}")

        u = test_get_test_user()

        # Get all present/enabled images 
        list_images = Image.objects.filter(present=True, imagetype=Image.TP_PROJECT)
        # Combine QuerySets using union
        list_images = list_images | Image.objects.filter(present=True, imagetype=Image.TP_JOB)

        logger.debug("Create and launch test containers %d", len(list_images))
        list_new_containers = []
        # Create test environments with the filtered imagetypes
        for image in list_images:
            new_c = test_create_env(user=u, image=image)
            list_new_containers.append(new_c)
            new_c.node = 'onco1'
            new_c.save()
            new_c.start()
            sleep(1)

        succeeded = []
        failed = []
        finished = []
        
        logger.debug("Waiting for containers to start")
        sleep(10)
        # check container state every n seconds
        while len(list_new_containers) != len(finished):
            logger.debug("%d out of %d is running", len(finished), len(list_new_containers))
            sleep(5)
            logger.debug("Check test container state:")
            for c in list_new_containers:
                if c in finished:
                    continue
                if check_container_running(c):
                    if check_container_error(c):
                        failed.append(c)
                        logger.debug("%s is in error state -> so stopping", c.name)
                    else:
                        succeeded.append(c)
                        logger.debug("%s is running fine -> so stopping", c.name)

                    finished.append(c)
                    c.stop()
                else:
                    logger.debug("%s is not running yet", c.name)

        logger.debug("Delete test containers")
        for c in list_new_containers:
            logger.debug("Deleting %s", c.name)
            c.delete()

        logger.info("Summary: %d succeeded, %d failed", len(succeeded), len(failed))
        if len(failed) > 0:
            logger.debug("Failed containers:")
            for c in failed:
                logger.info("%s (%s)", c.name, c.image.name)
        logger.info(f"TEST COMPLETED: {__name__}")
