from container.models import Image, ProxyImageBinding
from django.core.management.base import BaseCommand
import time
import logging

from test.utils import test_create_env, test_get_test_user

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test adding and removing proxy routes to a container"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")

        u = test_get_test_user()

        # Get all present/enabled images 
        image = Image.objects.filter(present=True)
        image = image[(len(image)-1)]
        new_c = test_create_env(user=u, image=image)
        try:
            logger.debug(f"Container {new_c.label} created")
            logger.debug(f"Adding proxy to container {new_c.label}")
            for pib in ProxyImageBinding.objects.filter(image=image):
                pib.proxy.addroute(new_c)
                logger.debug(f"Proxy route added {pib.proxy} -> {new_c.label}")

            time.sleep(2)
            logger.debug(f"Removing proxy to container {new_c.label}")
            for pib in ProxyImageBinding.objects.filter(image=image):                
                pib.proxy.removeroute(new_c)
                logger.debug(f"Proxy route removed {pib.proxy} -> {new_c.label}")
            logger.debug(f"TEST COMPLETED: {__name__}")
        except Exception as e:
            logger.debug(e)
            logger.debug("ERROR occurred while adding/removing proxy route")
        finally:
            new_c.delete()

