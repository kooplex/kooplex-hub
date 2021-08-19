import logging
import pwgen

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete

from ..models import *

logger = logging.getLogger(__name__)


@receiver(pre_save, sender = Course)
def mkdir_course(sender, instance, **kwargs):
    from kooplexhub.lib.filesystem import mkdir_course
    mkdir_course(instance)


@receiver(pre_delete, sender = Course)
def garbagedir_course(sender, instance, **kwargs):
    from kooplex.lib.filesystem import delete_course
    delete_course(instance)


@receiver(pre_save, sender = UserCourseBinding)
def mkdir_usercourse(sender, instance, **kwargs):
    from kooplexhub.lib.filesystem import mkdir_course_workdir
    mkdir_course_workdir(instance)


@receiver(pre_delete, sender = UserCourseBinding)
def delete_usercourse(sender, instance, **kwargs):
    from kooplexhub.lib.filesystem import delete_usercourse
    delete_usercourse(instance)





