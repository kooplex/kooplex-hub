import os
import pwgen
import logging
import unidecode

from django.db import models
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from kooplex.settings import KOOPLEX
from kooplex.lib.filesystem import Dirname

logger = logging.getLogger(__name__)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    bio = models.TextField(max_length = 500, blank = True)
    location = models.CharField(max_length = 30, blank = True)
    userid = models.IntegerField(null = False)
    token = models.CharField(max_length = 64, null = True)
    can_createproject = models.BooleanField(default = False) 

    @property
    def name(self):
        return '{} {}'.format(self.user.first_name, self.user.last_name)

    @property
    def username(self):
        return '{}'.format(self.user.username)

    @property
    def safename(self):
        return "%s_%s" % (unidecode.unidecode(self.user.last_name), unidecode.unidecode(self.user.first_name).replace(' ', ''))

    @property
    def everybodyelse(self):
        return Profile.objects.filter(~models.Q(id = self.id) & ~models.Q(user__is_superuser = True))

    def everybodyelse_like(self, pattern):
        return Profile.objects.filter(~models.Q(id = self.id) & ~models.Q(user__is_superuser = True) & (models.Q(user__username__icontains = pattern) | models.Q(user__first_name__icontains = pattern) | models.Q(user__last_name__icontains = pattern)))

    @property
    def groupid(self):
        return KOOPLEX.get('ldap', {}).get('gid_users', 1000)

    @property
    def projectbindings(self):
        from .project import UserProjectBinding
        for binding in UserProjectBinding.objects.filter(user = self.user):
            yield binding

    @property
    def containers(self):
        from .container import Container
        for container in Container.objects.filter(user = self.user):
             yield container

    @property
    def reports(self):
        from .report import Report
        from hub.forms import T_REPORTS, T_REPORTS_DEL
        reports_shown = set()
        for report in Report.objects.all():#FIXME: filter those you can see
             if report in reports_shown:
                 continue
             g = report.groupby()
             T = T_REPORTS_DEL(g) if self.user == report.creator else T_REPORTS(g)
             yield report.latest, T, report.directory_name
             reports_shown.update(set(g))

    def usercoursebindings(self, **kw):
        from .course import UserCourseBinding
        for binding in UserCourseBinding.objects.filter(user = self.user, **kw):
            yield binding

    @property
    def is_teacher(self):
        return len(list(self.usercoursebindings(is_teacher = True))) > 0

    def courses_taught(self):
        return set([ binding.course for binding in self.usercoursebindings(is_teacher = True) ])

    @property
    def is_student(self):
        return len(list(self.usercoursebindings(is_teacher = False))) > 0

    def courses_attend(self):
        return set([ binding.course for binding in self.usercoursebindings(is_teacher = False) ])

    def is_coursecodeteacher(self, coursecode):
        from .course import UserCourseCodeBinding
        try:
            UserCourseCodeBinding.objects.get(user = self.user, coursecode = coursecode, is_teacher = True)
            return True
        except UserCourseCodeBinding.DoesNotExist:
            return False

    @property
    def courseprojects_attended(self): #FIXME
        duplicate = set()
        for coursebinding in self.coursebindings:
            if not coursebinding.is_teacher:
                if coursebinding.course.project in duplicate:
                    continue
                yield coursebinding.course.project
                duplicate.add(coursebinding.course.project)

    def dirs_reportprepare(self):
        dir_reportprepare = Dirname.reportprepare(self.user)
        for d in os.listdir(dir_reportprepare):
            if d.startswith('.'):
                continue
            if os.path.isdir(os.path.join(dir_reportprepare, d)):
                yield d
 
    def files_reportprepare(self):
        dir_prefix = Dirname.reportprepare(self.user)
        dirs = self.dirs_reportprepare()
        for d in dirs:
            for f in os.listdir("%s/%s"%(dir_prefix, d)):
                if f.endswith('.ipynb') or f.endswith('.html') or f.endswith('.py'):
                    yield f

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

    @property
    def vctokens(self):
        from .versioncontrol import VCToken
        for t in VCToken.objects.filter(user = self.user):
            yield t
   
    @property
    def fstokens(self):
        from .filesync import FSToken
        for t in FSToken.objects.filter(user = self.user):
            yield t


@receiver(post_save, sender = User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        logger.info("New user %s" % instance)
        last_uid = Profile.objects.all().aggregate(models.Max('userid'))['userid__max']
        uid = KOOPLEX.get('min_userid', 1000) if last_uid is None else last_uid + 1
        token = pwgen.pwgen(64)
        Profile.objects.create(user = instance, userid = uid, token = token)


@receiver(post_save, sender = User)
def create_user_home_and_reportprepare(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import mkdir_home, mkdir_reportprepare, mkdir_usergarbage
    if created:
        try:
            mkdir_home(instance)
            mkdir_reportprepare(instance)
            mkdir_usergarbage(instance)
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


