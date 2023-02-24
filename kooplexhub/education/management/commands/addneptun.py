import json
import logging
  
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from education.models import Course, UserCourseBinding

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create course groups for those courses, where it is missing"

    def add_arguments(self, parser):
        parser.add_argument('--course', help = "Course's name", nargs = 1)
        parser.add_argument('--neptun', help = "Filename of the list of neptun codes", nargs = 1)

    def handle(self, *args, **options):
        try:
            c = Course.objects.get(name = options.get('course')[0])
        except Course.DoesNotExist:
            print ("EE: course not found. Known courses are:\n{}".format(", ".join(map(lambda c: c.name, Course.objects.all()))))
            return
        N = 0
        for fn in options.get('neptun'):
            with open(fn) as f:
                for n in f:
                    n = n.strip().lower()
                    try:
                        u = User.objects.get(username = n)
                        b, created = UserCourseBinding.objects.get_or_create(user = u, course = c, is_teacher = False)
                        if created:
                            print (f"OK: created {b}")
                            N += 1
                        else:
                            print (f"WW: exists {b}")
                    except User.DoesNotExist:
                        print (f"EE: not registered student {n}")

        print (f'{N} students added to course {c}')

