import os
import logging
import json

from django.core.management.base import BaseCommand, CommandError

from hub.models import Container, Report

from kooplex.lib.proxy import getroutes, addroute, droproutes


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Remove all proxy targets and reload those currently in use'

    def add_arguments(self, parser):
        parser.add_argument('--dry', help = "Dry run: list proxy tergets to load", action = "store_true")
    
    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        if options['dry']:
            print ("dry run")
            resp = getroutes()
            routes = json.loads(resp.content.decode())
            for r, v in routes.items():
                print ("remove %s [--> %s]" % (r, v['target']))
            print ("----")
        else:
            droproutes()
        for c in Container.objects.filter(state = Container.ST_RUNNING):
            if options['dry']:
                print ("%s --> %s" % (c.proxy_path, c.url))
            else:
                addroute(c)
        for r in Report.objects.all():
            if options['dry']:
                target_url = os.path.join('http://kooplex-test-report-nginx') # FIXME: settings.py
                print ("%s --> %s" % (r.proxy_path, target_url))
            else:
                addroute(r)

