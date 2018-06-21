import pwgen
import logging

from django.db import models
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    bio = models.TextField(max_length = 500, blank = True)
    location = models.CharField(max_length = 30, blank = True)
    userid = models.IntegerField(null = False)
    token = models.CharField(max_length = 64, null = True)
    can_createproject = models.BooleanField(default = False) 

    @property
    def groupid(self):
        return KOOPLEX.get('ldap', {}).get('gid_users', 1000)

    @property
    def coursebindings(self):
        from .course import UserCourseBinding
        for binding in UserCourseBinding.objects.filter(user = self.user):
            yield binding

    @property
    def courseprojects_taught(self):
        duplicate = set()
        for coursebinding in self.coursebindings:
            if coursebinding.is_teacher:
                if coursebinding.course.project in duplicate:
                    continue
                yield coursebinding.course.project
                duplicate.add(coursebinding.course.project)

    @property
    def is_teacher(self):
        return len(list(self.courseprojects_taught)) > 0

    def is_courseteacher(self, course):
        for binding in self.coursebindings:
            if binding.course != course:
                continue
            return binding.is_teacher
        return False

    @property
    def courseprojects_attended(self):
        duplicate = set()
        for coursebinding in self.coursebindings:
            if not coursebinding.is_teacher:
                if coursebinding.course.project in duplicate:
                    continue
                yield coursebinding.course.project
                duplicate.add(coursebinding.course.project)
 
    @property
    def is_student(self):
        return len(list(self.courseprojects_attended)) > 0

    @property
    def functional_volumes(self):
        from .volume import Volume
        for volume in Volume.filter(Volume.FUNCTIONAL):
            yield volume

    @property
    def storage_volumes(self):
        from .volume import Volume
        for volume in Volume.filter(Volume.STORAGE, user = self.user):
            yield volume
   

@receiver(post_save, sender = User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        logger.info("New user %s" % instance)
        last_uid = Profile.objects.all().aggregate(models.Max('userid'))['userid__max']
        uid = KOOPLEX.get('min_userid', 1000) if last_uid is None else last_uid + 1
        token = pwgen.pwgen(64)
        Profile.objects.create(user = instance, userid = uid, token = token)


@receiver(post_save, sender = User)
def create_user_home(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import mkdir_home
    if created:
        try:
            mkdir_home(instance)
        except Exception as e:
            logger.error("Failed to create home for %s -- %s" % (instance, e))


@receiver(post_delete, sender = Profile)
def remove_django_user(sender, instance, **kwargs):
    instance.user.delete()
    logger.info("Deleted user %s" % instance.user)


@receiver(pre_delete, sender = User)
def garbage_user_home(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbagedir_home
    garbagedir_home(instance)


@receiver(post_save, sender = User)
def ldap_create_user(sender, instance, created, **kwargs):
    from kooplex.lib.ldap import Ldap
    regenerate = False
    try:
        ldap = Ldap()
        response = ldap.get_user(instance)
        uidnumber = response.get('attributes', {}).get('uidNumber')
        if uidnumber != instance.profile.userid:
            ldap.removeuser(instance)
            regenerate = True
    except Exception as e:
        logger.error("Failed to get ldap entry for %s -- %s" % (instance, e))
    if created or regenerate:
        try:
            ldap.adduser(instance)
        except Exception as e:
            logger.error("Failed to create ldap entry for %s -- %s" % (instance, e))


@receiver(post_delete, sender = User)
def ldap_delete_user(sender, instance, **kwargs):
    from kooplex.lib.ldap import Ldap
    try:
        Ldap().removeuser(instance)
    except Exception as e:
        logger.error("Failed to remove ldap entry for %s -- %s" % (instance, e))


