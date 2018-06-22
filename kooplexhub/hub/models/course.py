import os
import logging

from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from .project import Project

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Course(models.Model):
    courseid = models.CharField(max_length = 30, null = False)
    description = models.TextField(max_length = 500, blank = True)
    project = models.OneToOneField(Project)

    def __str__(self):
        return "<Course: %s>" % self.courseid

    def list_userflags(self, user):
        for coursebinding in UserCourseBinding.objects.filter(user = user, course = self):
            yield coursebinding.flag if coursebinding.flag else "_"

    @register.filter
    def lookup_usercourseflags(self, user):
        return ", ".join(list(self.list_userflags(user)))

    @property
    def groupid(self):
        from .group import Group
        try:
            group = Group.objects.get(project = self.project)
            return group.groupid if group.is_active else 0
        except Exception as e:
            logger.error("No groupid for course %s" % self)
            return 0

class UserCourseBinding(models.Model):
    user = models.ForeignKey(User, null = False)
    course = models.ForeignKey(Course, null = False)
    flag = models.CharField(max_length = 32, null = True)
    is_teacher = models.BooleanField(default = False)
    is_protected = models.BooleanField(default = False)

    def __str__(self):
        return "<UserCourseBinding: %s %s/%s>" % (self.user, self.course, self.flag)

@receiver(post_save, sender = Course)
def mkdir_course(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import mkdir_course_share
    if created:
        mkdir_course_share(instance)

@receiver(post_delete, sender = Course)
def garbagedir_course(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbagedir_course_share, rmdir_course_workdir
    garbagedir_course_share(instance)
    rmdir_course_workdir(instance)

@receiver(post_save, sender = Course)
def bind_coursevolumes(sender, instance, created, **kwargs):
    from .volume import Volume, VolumeProjectBinding
    if created:
        for key in [ Volume.HOME, Volume.COURSE_SHARE, Volume.COURSE_WORKDIR ]:
            try:
                volume = Volume.lookup(key)
                binding = VolumeProjectBinding.objects.create(project = instance.project, volume = volume)
                logger.debug("binding created %s" % binding)
            except Volume.DoesNotExist:
                logger.error("cannot create binding course %s volume %s" % (instance, key['tag']))

@receiver(post_save, sender = UserCourseBinding)
def mkdir_usercourse(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import mkdir_course_workdir, grantacl_course_workdir, grantacl_course_share
    if created:
        mkdir_course_workdir(instance)
        grantacl_course_workdir(instance)
        grantacl_course_share(instance)

@receiver(pre_delete, sender = UserCourseBinding)
def movedir_usercourse(sender, instance, **kwargs):
    from kooplex.lib.filesystem import archive_course_workdir, revokeacl_course_workdir, revokeacl_course_share
    archive_course_workdir(instance)
    revokeacl_course_workdir(instance)
    revokeacl_course_share(instance)

@receiver(post_save, sender = UserCourseBinding)
def create_usercourseproject(sender, instance, created, **kwargs):
    from .project import UserProjectBinding
    if created:
        try:
            UserProjectBinding.objects.get(user = instance.user, project = instance.course.project)
        except UserProjectBinding.DoesNotExist:
            b = UserProjectBinding.objects.create(user = instance.user, project = instance.course.project)
            logger.info("New UserProjectBinding %s" % b)

def lookup_course(courseid):
    try:
        course = Course.objects.get(courseid = courseid)
    except Course.DoesNotExist:
        try:
            project = Project.objects.get(name = 'c_%s' % courseid)
            logger.debug("Course %s associated project found" % courseid)
        except Project.DoesNotExist:
            project = Project.objects.create(name = 'c_%s' % courseid)
            logger.debug("Course %s associated project created" % courseid)
        course = Course.objects.create(courseid = courseid, project = project)
        logger.warn('Course with courseid %s is created. Provide a description in admin panel' % courseid)
    return course

def update_UserCourseBindings(user, newbindings):
    bindings = list(UserCourseBinding.objects.filter(user = user))
    for newbinding in newbindings:
        course = newbinding['course']
        flag = newbinding['flag']
        is_teacher = newbinding['is_teacher']
        try:
            binding = UserCourseBinding.objects.get(user = user, course = course, flag = flag, is_teacher = is_teacher)
            if binding in bindings:
                bindings.remove(binding)
            continue
        except UserCourseBinding.DoesNotExist:
            UserCourseBinding.objects.create(user = user, course = course, flag = flag, is_teacher = is_teacher)
            logger.info("User %s binds to course %s/%s (is teacher: %s)" % (user, course, flag, is_teacher))
    for binding in bindings:
        if binding.is_protected:
            logger.warn("According to IDP user %s is not bound to course %s any longer. Binding is not removed because it is protected" % (user, binding.course))
        else:
            logger.info("User %s is not bound to course %s any longer" % (user, binding.course))
            binding.delete()

