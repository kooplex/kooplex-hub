import json
import logging
  
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub.lib import dirname
from hub.models import Group, FilesystemTask
from education.models import Course

logger = logging.getLogger(__name__)

code = lambda x: json.dumps([ i.id for i in x ])


class Command(BaseCommand):
    help = "Create course groups for those courses, where it is missing"

    def add_arguments(self, parser):
        parser.add_argument('--fix-fs', help = "Also fix filesystem permissions", action = 'store_true')

    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        for c in Course.objects.all():
            with transaction.atomic():
                g, created = Group.objects.select_for_update().get_or_create(name = c.cleanname, grouptype = Group.TP_COURSE) 
            if created:
                print (f'Course: {c} now maps to {g}')
                if options.get('fix_fs'):
                    FilesystemTask.objects.create(
                        folder = dirname.course_public(c),
                        groups_ro = code([g]),
                        task = FilesystemTask.TSK_GRANT
                    )
            else:
                print (f'Course: {c} maps to group {g} nothing to do')

