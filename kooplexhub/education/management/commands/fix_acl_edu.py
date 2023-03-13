import time
import json
import sys
import logging
  
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub.lib import dirname
from hub.models import Group
from education.models import Course, UserAssignmentBinding
from education.filesystem import *
from hub.lib import grantaccess_group, grantaccess_user

logger = logging.getLogger(__name__)



class Command(BaseCommand):
    help = "Make sure assignment folders already handed out get proper user permissions"

    def add_arguments(self, parser):
        parser.add_argument('--course', help = "Select course to handle", nargs = '+')


    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        C = options.get('course')
        if C is None:
            print ('WW: available courses: {}'.format(', '.join(map(lambda x: x.name, Course.objects.all()))))
            sys.exit(0)
        for c in C:
            try:
                course = Course.objects.get(name = c)
                group_students = course.group_students
                group_teachers = course.group_teachers
                # Check course folders
                f_public = course_public(course)
                f_prepare = course_assignment_prepare_root(course)
                f_assignment = course_assignment_root(course)
                f_correct = assignment_correct_root(course)
                grantaccess_group(group_students, f_public, readonly = True, recursive = True)
                grantaccess_group(group_students, f_public, readonly = True, follow = True, recursive = True)
                grantaccess_group(group_teachers, f_public, readonly = False, recursive = True)
                grantaccess_group(group_teachers, f_public, readonly = False, follow = True, recursive = True)

                grantaccess_group(group_teachers, f_prepare, readonly = False, recursive = True)
                grantaccess_group(group_teachers, f_prepare, readonly = False, follow = True, recursive = True)

                grantaccess_group(group_students, f_assignment, readonly = True, recursive = True)
                grantaccess_group(group_students, f_assignment, readonly = True, follow = True, recursive = True)
                grantaccess_group(group_teachers, f_assignment, readonly = True, recursive = True)
                grantaccess_group(group_teachers, f_assignment, readonly = True, follow = True, recursive = True)

                grantaccess_group(group_teachers, f_correct, readonly = True, recursive = True)
                grantaccess_group(group_teachers, f_correct, readonly = True, follow = True, recursive = True)
                # Check assignment folders
                for uab in UserAssignmentBinding.objects.filter(assignment__course = course):
                    folder = dirname.assignment_workdir(uab),
                    grantaccess_group(group_teachers, folder, readonly = True, recursive = True)
                    grantaccess_group(group_teachers, folder, readonly = True, follow = True, recursive = True)
                    grantaccess_user(uab.user, folder, readonly = False, recursive = True)
                    grantaccess_user(uab.user, folder, readonly = False, follow = True, recursive = True)
            except Exception as e:
                print (f'EE: {e}')


