import os
import logging

from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from .project import Project

from kooplex.settings import KOOPLEX
from kooplex.lib import standardize_str
from kooplex.lib.filesystem import Dirname

logger = logging.getLogger(__name__)

class Course(models.Model):
    courseid = models.CharField(max_length = 30, null = False)
    description = models.TextField(max_length = 500, blank = True)
    project = models.OneToOneField(Project)

    def __str__(self):
        return "<Course: %s>" % self.courseid

    @property
    def safecourseid(self):
        return standardize_str(self.courseid)

    def list_userflags(self, user):
        for coursebinding in UserCourseBinding.objects.filter(user = user, course = self):
            yield coursebinding.flag if coursebinding.flag else "_"

    @register.filter
    def lookup_usercourseflags(self, user):
        return list(self.list_userflags(user))

    @register.filter
    def lookup_userassignmentbindings(self, student):
        from .assignment import Assignment, UserAssignmentBinding
        flags = self.lookup_usercourseflags(student)
        if len(flags) > 0:
            logger.error("Student %s has more flags (%s) for course %s, assuming first item" % (student, flags, self.courseid))
        flag = None if flags[0] == '_' else flags[0]
        assignments = list(Assignment.objects.filter(course = self, flag = flag))
        for binding in UserAssignmentBinding.objects.filter(user = student):
            if binding.assignment in assignments:
                yield binding

    @register.filter
    def lookup_userassignmentbindings_submitted(self, teacher):
        from .assignment import Assignment, UserAssignmentBinding
        bindings = set()
        for assignment in Assignment.objects.filter(course = self):
            if assignment.creator != teacher and len(UserCourseBinding.objects.filter(user = teacher, course = self, flag = assignment.flag, is_teacher = True)) == 0:
                continue
            bindings.update(UserAssignmentBinding.objects.filter(assignment = assignment, state = UserAssignmentBinding.ST_SUBMITTED))
            bindings.update(UserAssignmentBinding.objects.filter(assignment = assignment, state = UserAssignmentBinding.ST_COLLECTED))
        return bindings

    @register.filter
    def lookup_userassignmentbindings_correcting(self, teacher):
        from .assignment import Assignment, UserAssignmentBinding
        bindings = set()
        for assignment in Assignment.objects.filter(course = self):
            if assignment.creator != teacher and len(UserCourseBinding.objects.filter(user = teacher, course = self, flag = assignment.flag, is_teacher = True)) == 0:
                continue
            bindings.update(UserAssignmentBinding.objects.filter(assignment = assignment, corrector = teacher, state = UserAssignmentBinding.ST_CORRECTING))
        return bindings

    @register.filter
    def count_students4flag(self, flag):
        return len(UserCourseBinding.objects.filter(course = self, flag = flag, is_teacher = False))

    @property
    def groupid(self):
        from .group import Group
        try:
            group = Group.objects.get(project = self.project)
            return group.groupid if group.is_active else 0
        except Exception as e:
            logger.error("No groupid for course %s" % self)
            return 0

    def listdirs_private(self):
        dir_courseprivate = Dirname.courseprivate(self)
        for d in os.listdir(dir_courseprivate):
            if os.path.isdir(os.path.join(dir_courseprivate, d)):
                yield d

    def dirs_assignmentcandidate(self):
        from .assignment import Assignment
        candidates = []
        for d in self.listdirs_private():
            if d in ['.ipynb_checkpoints']:
                continue
            assignments = set(Assignment.objects.filter(course = self, folder = d))
            if len(assignments) == 0:
                candidates.append(d)
        return candidates

    def collectableassignments(self):
        from .assignment import Assignment, UserAssignmentBinding
        collectable = []
        for assignment in Assignment.objects.filter(course = self):
            bindings = UserAssignmentBinding.objects.filter(assignment = assignment, state = UserAssignmentBinding.ST_WORKINPROGRESS)
            if len(bindings):
                collectable.append(assignment)
        return collectable


class UserCourseBinding(models.Model):
    user = models.ForeignKey(User, null = False)
    course = models.ForeignKey(Course, null = False)
    flag = models.CharField(max_length = 32, null = True)
    is_teacher = models.BooleanField(default = False)
    is_protected = models.BooleanField(default = False)

    def __str__(self):
        return "<UserCourseBinding: %s %s/%s>" % (self.user, self.course, self.flag)

    @property
    def assignments(self):
        from .assignment import Assignment
        for a in Assignment.objects.filter(course = self.course, flag = self.flag):
            #FIXME: check expiry date
            yield a


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
        for key in [ Volume.HOME, Volume.COURSE_SHARE, Volume.COURSE_WORKDIR, Volume.COURSE_ASSIGNMENTDIR ]:
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
    safe_courseid = standardize_str(courseid)
    try:
        course = Course.objects.get(courseid = courseid)
    except Course.DoesNotExist:
        try:
            project = Project.objects.get(name = 'c_%s' % safe_courseid)
            logger.debug("Course %s associated project found" % courseid)
        except Project.DoesNotExist:
            project = Project.objects.create(name = 'c_%s' % safe_courseid)
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

