import os
import logging
  
from django.core.management.base import BaseCommand
from education.models import Course, UserAssignmentBinding
from education.filesystem import *
from hub.lib.filesystem import _rmdir

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Cleanup directories"

    def add_arguments(self, parser):
        parser.add_argument('--course', help = "Select course to handle", nargs = '+', required = True)
        parser.add_argument('--dry', help = "Show what is to be removed but do not actually remove", action = 'store_true')

    def handle(self, *args, **options):
        print ("call %s %s" % (args, options))
        for name in options['course']:
            try:
                c = Course.objects.get(name = name)
                correct_dir = assignment_correct_root(c) 
                fs_dirs = [] 
                for d_a in os.listdir(correct_dir):
                    for d_u in os.listdir(os.path.join(correct_dir, d_a)):
                        fs_dirs.append( os.path.join(correct_dir, d_a, d_u) )
                fs_keep = [ assignment_correct_dir(b) for b in UserAssignmentBinding.objects.filter(assignment__course = c) ]
                for d in set(fs_dirs).difference(fs_keep):
                    print (f"Deleting folder {d}")
                    if not options['dry']:
                        _rmdir(d)
            except:
                raise


