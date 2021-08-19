import os
import logging
import json

from django.core.management.base import BaseCommand, CommandError

from kooplex.lib.filesync import impersonator_sync
from hub.models import FSLibrary

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start impersonator sync processes'

    def add_arguments(self, parser):
        parser.add_argument('--dry', help = "Dry run", action = "store_true")
    
    def _do_it(self, l, dry = True):
        try:
            if dry:
                print (f'should sync {l.library_name}')
                return
            f = impersonator_sync(l, 'start')
            print (f'started syncing {l.library_name} in folder {f}')
            logger.info(f'started syncing {l.library_name} in folder {f}')
        except AssertionError as e:
            logger.warning("Problem: %s" % e)
            print("Problem: %s" % e)

    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        for l in FSLibrary.objects.filter(syncing = True):
            self._do_it(l, dry = options['dry'])


