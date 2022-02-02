import logging
  
from django.core.management.base import BaseCommand, CommandError
from hub.models import Group
from education.models import Course

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "List courses and corresponding groups"


    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        for c in Course.objects.all():
            try:
                g = Group.objects.get(name = c.cleanname, grouptype = Group.TP_COURSE)
                print (f'Course: {c} maps to group {g}')
            except Group.DoesNotExist:
                print (f'Course: {c} MISSING GROUP')

