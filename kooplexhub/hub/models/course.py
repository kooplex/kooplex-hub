import os
import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from .project import Project

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Course(models.Model):
    courseid = models.CharField(max_length = 30, null = False)
    description = models.TextField(max_length = 500, blank = True)

    def __str__(self):
        return "<Course: %s>" % self.courseid

    def list_userflags(self, user):
        for coursebinding in UserCourseBinding.objects.filter(user = user, course = self):
            yield coursebinding.flag if coursebinding.flag else "_"

    @register.filter
    def lookup_usercourseflags(self, user):
        return ", ".join(list(self.list_userflags(user)))

    @property
    def project(self):
        return CourseProjectBinding.objects.get(course = self).project

class CourseProjectBinding(models.Model):
    course = models.ForeignKey(Course, null = False)
    project = models.ForeignKey(Project, null = False)

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
    from kooplex.lib.filesystem import _mkdir
    if created:
        folder_courseprivate = os.path.join(KOOPLEX.get('mountpoint', {}).get('course'), instance.courseid, 'private')
        _mkdir(folder_courseprivate)
        folder_coursepublic = os.path.join(KOOPLEX.get('mountpoint', {}).get('course'), instance.courseid, 'public')
        _mkdir(folder_coursepublic)
        logger.info("course %s directories created" % instance)

@receiver(post_save, sender = Course)
def create_courseproject(sender, instance, created, **kwargs):
    if created:
        try:
            binding = CourseProjectBinding.objects.get(course = instance)
            logger.debug("Binding is present %s" % binding)
            return
        except CourseProjectBinding.DoesNotExist:
            project = Project.objects.create(name = 'c_%s' % instance.courseid)
            CourseProjectBinding.objects.create(course = instance, project = project)
            logger.warn("Project %s for course %s is created and bound. Please specify image and description." % (project, instance))

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
    from kooplex.lib.filesystem import _mkdir
    if created:
        if instance.flag:
            folder_usercourse = os.path.join(KOOPLEX.get('mountpoint', {}).get('usercourse'), instance.course.courseid, instance.flag, instance.user.username)
        else:
            folder_usercourse = os.path.join(KOOPLEX.get('mountpoint', {}).get('usercourse'), instance.course.courseid, '_', instance.user.username)
        _mkdir(folder_usercourse)
        #FIXME: set acl
        logger.info("created %s" % (folder_usercourse))

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
        logger.warn('Course with courseid %s is going to be created. Provide a description in admin panel' % courseid)
        course = Course.objects.create(courseid = courseid)
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

