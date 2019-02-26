import os
import logging
import json

from django.core.management.base import BaseCommand, CommandError

from django.contrib.auth.models import User

from kooplex.lib.filesystem import check_home, mkdir_home 
from kooplex.lib.filesystem import check_usergarbage, mkdir_usergarbage 
from kooplex.lib.filesystem import check_reportprepare, mkdir_reportprepare

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Make sure folder structure is up to date'

    def add_arguments(self, parser):
        parser.add_argument('--dry', help = "Dry run: do not actually create the folders", action = "store_true")
    
    def _do_it(self, description, f_check, f_mkdir, arg, dry = True):
        try:
            f_check(arg)
        except AssertionError as e:
            logger.warning("Problem: %s" % e)
            if not dry:
                f_mkdir(arg)
                print (description, arg)

    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        for u in User.objects.all():
            self._do_it("Create home folder", check_home, mkdir_home, u, dry = options['dry'])
            self._do_it("Create garbage folder", check_usergarbage, mkdir_usergarbage, u, dry = options['dry'])
            self._do_it("Create report prepare folder", check_reportprepare, mkdir_reportprepare, u, dry = options['dry'])

