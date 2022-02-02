import logging
  
from django.core.management.base import BaseCommand, CommandError
from hub.models import UserGroupBinding, Group
from education.models import UserCourseBinding

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "List student course mappings and corresponding groups"


    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        for bc in UserCourseBinding.objects.all():
            try:
                bg = UserGroupBinding.objects.get(user = bc.user, group__name = bc.course.cleanname, group__grouptype = Group.TP_COURSE)
                print (f'OK: {bc} maps to {bg}')
                continue
            except UserGroupBinding.DoesNotExist:
                pass
            try:
                g = Group.objects.get(name = bc.course.cleanname, grouptype = Group.TP_COURSE)
                bg = UserGroupBinding.objects.create(user = bc.user, group = g)
                print (f'CREATED: {bc} maps to {bg}')
            except Group.DoesNotExist:
                print ("ERROR: {bc} group is missing")

