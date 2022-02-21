import time
import json
import sys
import logging
  
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub.lib import dirname
from hub.models import FilesystemTask
from education.models import Course, UserAssignmentBinding

logger = logging.getLogger(__name__)

code = lambda x: json.dumps([ i.id for i in x ])


class Command(BaseCommand):
    help = "Make sure assignment folders already handed out get proper user permissions"

    def add_arguments(self, parser):
        parser.add_argument('--course', help = "Select course to handle", nargs = '+')

    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        C = options.get('course')
        if C is None:
            print ('WW: available courses: {}'.format(', '.join(map(lambda x: x.cleanname, Course.objects.all()))))
            sys.exit(0)
        for c in C:
            try:
                co = Course.objects.get(cleanname = c)
                for uab in UserAssignmentBinding.objects.filter(assignment__course = co):
                    FilesystemTask.objects.create(
                        folder = dirname.assignment_workdir(uab),
                        users_rw = code([uab.user]),
                        users_ro = code([ teacherbinding.user for teacherbinding in uab.assignment.course.teacherbindings ]),
                        recursive = True,
                        task = FilesystemTask.TSK_GRANT
                    )
                    print (f'Course: {c} {uab} fix')
                    time.sleep(.02) # avoid flooding database
            except Exception as e:
                print (f'EE: {e}')


