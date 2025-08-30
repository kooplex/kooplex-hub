import time
import json
import sys
import logging
  
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from container.models import Container

logger = logging.getLogger(__name__)



class Command(BaseCommand):
    help = "When proxy restarts register running project containers"

    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        for c in Container.objects.filter(state=Container.State.RUNNING, image__imagetype='projectimage'):
            print(c)
            c.addroutes()

