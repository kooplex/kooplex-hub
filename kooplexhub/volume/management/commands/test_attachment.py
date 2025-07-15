# Create attachment 
# mount it
# check permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from test.utils import run_env_start_stop

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create and delete a project with a user"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")
       