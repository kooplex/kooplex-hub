from django.core.management.base import BaseCommand
from container.models import Image
from hub.models import User
from time import sleep
from test.utils import *
import logging

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test available images by creating, starting, and stopping containers"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")

        u = test_get_test_user()

        # Get all present/enabled images 
        list_images = Image.objects.filter(present=True)

        logger.debug("Create and launch test containers %d", len(list_images))
        list_new_containers = []
        # Create test environments with the filtered imagetypes
        for image in list_images:
            new_c = test_create_env(user=u, image=image)
            list_new_containers.append(new_c)
            new_c.start()
            sleep(1)

        finished = []

        logger.debug("Waiting for containers to start")
        # check container state every n seconds
        while len(list_new_containers) != len(finished):
            logger.debug("%d out of %d is running", len(finished), len(list_new_containers))
            sleep(1)
            logger.debug("Check test container state:")
            for c in list_new_containers: 
                istherelog = len(c.retrieve_log()) > 0
                logger.debug("%s %s %s", c.image.present, c.name, istherelog)
            sleep(1)
            for c in list_new_containers:
                if check_container_running(c):
                    logger.debug("%s is running -> so stopping", c.name)
                    finished.append(c)
                    c.stop()
                else:
                    logger.debug("%s is not running yet", c.name)

        logger.debug("Delete test containers")
        for c in list_new_containers:
            logger.debug("Deleting %s", c.name)
            c.delete()
        logger.debug(f"TEST COMPLETED: {__name__}")
