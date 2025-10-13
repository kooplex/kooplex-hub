from django.core.management.base import BaseCommand
from container.models import Image
from hub.models import User
from time import sleep
from test.utils import *
import logging
import random

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Tests images sequentially for a randomly selected user"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Test all images else just one random image")
        parser.add_argument("--one", action="store_true", help="Test just one random image")

    def handle(self, *args, **options):
        logger.info(f"TEST: {__name__}")

        user = test_get_test_user()
        if options['all']:
            logger.debug("Testing all images")
            images = list(Image.objects.filter(present=True))
        elif options['one']:
            images = [(Image.objects.get(name=options['one']))]
        else:
            images = [random.choice(list(Image.objects.filter(present=True)))]

        succeeded = []
        failed = []

        for selected_image in images:
            logger.debug("Create and launch test container %s", selected_image)
        
            # Create test environments with the filtered imagetypes
            new_c = test_create_env(user=user, image=selected_image)
            new_c.start()
            sleep(1)

            status = 'starting'
            counter = 0
            # check container state every n seconds
            while status != 'running' and counter < 30:
                sleep(5)
                counter += 5

                if check_container_running(new_c):
                    logger.debug("%s is RUNNING", new_c.name)
                    status = 'running'
                    succeeded.append(selected_image.name)
                else:
                    logger.debug("%s is NOT RUNNING yet", new_c.name)
                    logger.debug("LOG: %s", new_c.retrieve_log())
                    failed.append(selected_image.name)

            # Execute command in the pod to check permissions
            exec_command = f"whoami; su {user.username} -c 'whoami; echo $HOME'"
            resp = exec_command_in_pod(new_c, exec_command)
            logger.debug(f"Command output: {resp}")

            logger.debug("Stop and delete test container %s", new_c.name)
            new_c.stop()
            new_c.delete()
        
        logger.info(f"TEST FINISHED: {__name__}")
        logger.info(f"Succeeded images: {succeeded}")
        logger.info(f"Failed images: {failed}")
