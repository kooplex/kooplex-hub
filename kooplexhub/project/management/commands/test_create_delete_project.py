#test creation
#teest permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from test.utils import test_create_project

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create and delete a project with a user"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")
       
        try:
            logger.debug("Creating test project")
            p, upb = test_create_project()            
            p.delete()
            logger.debug(f"Project {p.name} deleted")
        except Exception as e:
            print(e)
        
            
