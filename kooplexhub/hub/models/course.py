import os
import logging

from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from .image import Image

from kooplex.settings import KOOPLEX
from kooplex.lib import standardize_str
from kooplex.lib.filesystem import Dirname, Filename

logger = logging.getLogger(__name__)


class Course(models.Model):
    name = models.CharField(max_length = 30, null = False)
    description = models.TextField(max_length = 500, blank = True)
    image = models.ForeignKey(Image, null = True)

    def __str__(self):
        return "Course: %s" % self.name

    @property
    def safename(self):
        return standardize_str(self.name)


    @register.filter
    def get_usercoursecontainer(self, user):
        from .container import CourseContainerBinding
        for binding in CourseContainerBinding.objects.filter(course = self):
            if binding.container.user == user:
                return binding.container #FIXME: the first container is returned

    @staticmethod
    def get_usercourse(course_id, user):
        course = Course.objects.get(id = course_id)
        for binding in UserCourseCodeBinding.objects.filter(user = user):
            if binding.coursecode.course == course:
                return course

    def coursecodes(self, user):
        for coursecode in CourseCode.objects.filter(course = self):
            try:
                UserCourseCodeBinding.objects.get(user = user, coursecode = coursecode)
                yield coursecode
            except UserCourseCodeBinding.DoesNotExist:
                pass

    @register.filter
    def coursecodes_joined(self, user):
        return ", ".join([ c.courseid for c in self.coursecodes(user) ])

    def count_coursecodestudents(self, coursecode):
        assert coursecode.course == self, "Coursecode missmatch %s and %s" % (self, coursecode)
        return len(UserCourseCodeBinding.objects.filter(coursecode = coursecode, is_teacher = False))

    @register.filter
    def lookup_userassignmentbindings(self, student):
        from .assignment import Assignment, UserAssignmentBinding
#FIXME
        assignments = list(Assignment.objects.filter(course = self))
        for binding in UserAssignmentBinding.objects.filter(user = student):
            if binding.assignment in assignments:
                yield binding

    def lookup_userassignmentbindings(self, **kw):
        from .assignment import Assignment, UserAssignmentBinding
        from django.db.models import Q
        logger.debug('filter: %s' % kw)
        extra_a = {}
        extra_b = {}
        if 'name' in kw:
            extra_a['name__icontains'] = kw['name']
        if 'state' in kw:
            extra_b['state'] = kw['state']
        user_name = kw.get('user', None)
        U = User.objects.filter(Q(last_name__icontains = user_name) | Q(first_name__icontains = user_name)) if 'user' in kw else None
        bindings = set()
        for assignment in Assignment.objects.filter(course = self, **extra_a):
            for binding in UserAssignmentBinding.objects.filter(assignment = assignment, **extra_b):
                if U is None or (U is not None and binding.user in U):
                    bindings.add(binding)
        return bindings


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
            okay = True
            if d in ['.ipynb_checkpoints']:
                continue
            for assignment in Assignment.objects.filter(folder = d):
                if assignment.coursecode.course == self:
                    okay = False
                    break
            if okay:
                candidates.append(d)
        return candidates

    def collectableassignments_2(self): #FIXME: refactor and give a better name
        from .assignment import Assignment, UserAssignmentBinding
        collectable = []
        for assignment in Assignment.objects.filter(course = self, is_massassignment = False):
            for binding in UserAssignmentBinding.objects.filter(assignment = assignment, state = UserAssignmentBinding.ST_WORKINPROGRESS):
                yield binding

    def collectableassignments(self):
#FIXME: can be a generator
        from .assignment import Assignment, UserAssignmentBinding
        collectable = []
        for assignment in Assignment.objects.filter(course = self, is_massassignment = True):
            bindings = UserAssignmentBinding.objects.filter(assignment = assignment, state = UserAssignmentBinding.ST_WORKINPROGRESS)
            if len(bindings):
                collectable.append(assignment)
        return collectable

#FIXME: deprecated
#    def report_mapping4user(self, user):
#        from .assignment import Assignment, UserAssignmentBinding
#        for assignment in Assignment.objects.filter(course = self):
#            for binding in UserAssignmentBinding.objects.filter(assignment = assignment, corrector = user):
#                mapping = binding.report_map(user)
#                if mapping:
#                    logger.debug(mapping)
#                    yield mapping
#            for binding in UserAssignmentBinding.objects.filter(assignment = assignment, user = user):
#                mapping = binding.report_map(user)
#                if mapping:
#                    logger.debug(mapping)
#                    yield mapping

    def bindableassignments(self):
        from .assignment import Assignment, UserAssignmentBinding
        bindable = []
        for coursecode in CourseCode.objects.filter(course = self):
            for assignment in Assignment.objects.filter(coursecode = coursecode, is_massassignment = False):
                for student in assignment.list_students_bindable():
                    binding = UserAssignmentBinding(assignment = assignment, user = student)
                    if not binding in bindable:
                        bindable.append(binding)
                        yield binding


    @register.filter
    def list_updatableassignments(self, teacher):
        from .assignment import Assignment
        assignment_candidates = list(Assignment.objects.filter(creator = teacher, course = self))
        #FIXME: extend with those assignments another teacher of the same course created
        assignments = []
        for a in assignment_candidates:
            sourcedir = os.path.join(Dirname.courseprivate(self), a.folder)
            if os.path.exists(sourcedir):
                assignments.append(a)
            else:
                logger.warning("Assignment source dir %s is missing" % sourcedir)
        return assignments


class CourseCode(models.Model):
    courseid = models.CharField(max_length = 30, null = False)
    course = models.ForeignKey(Course, null = True, default = None)

    def __str__(self):
        return self.courseid

    @property
    def safecourseid(self):
        return standardize_str(self.courseid)





class UserCourseCodeBinding(models.Model):
    user = models.ForeignKey(User, null = False)
    coursecode = models.ForeignKey(CourseCode, null = False)
    is_teacher = models.BooleanField(default = False)
    is_protected = models.BooleanField(default = False)

    def __str__(self):
        return "%s code: %s, teacher: %s" % (self.user, self.coursecode, self.is_teacher)

#FIXME:
class UserCourseBinding(models.Model):
    user = models.ForeignKey(User, null = False)
    course = models.ForeignKey(Course, null = False)
    is_teacher = models.BooleanField(default = False)
    is_protected = models.BooleanField(default = False)

    def __str__(self):
        return "%s code: %s, teacher: %s" % (self.user, self.course, self.is_teacher)

    @property
    def assignments(self):
        return []
        from .assignment import Assignment
        for a in Assignment.objects.filter(course = self.course):
            yield a

@receiver(post_save, sender = UserCourseCodeBinding)
def map_uccb2ucb(sender, instance, created, **kwargs):
    if instance.coursecode.course == None:
        logger.debug("No mapping this time %s has no course associated" % instance)
        return
    try:
        b = UserCourseBinding.objects.get(user = instance.user, course = instance.coursecode.course, is_teacher = instance.is_teacher)
        logger.debug("Mapping for %s is already present %s" % (instance, b))
        return
    except UserCourseBinding.DoesNotExist:
        b = UserCourseBinding.objects.create(user = instance.user, course = instance.coursecode.course, is_teacher = instance.is_teacher)
        logger.info("New mapping for %s: %s" % (instance, b))

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


#FIXME: EZ NEM KELL
@receiver(post_save, sender = Course)
def bind_coursevolumes(sender, instance, created, **kwargs):
    from .volume import Volume, VolumeCourseBinding
    if created:
        for key in [ Volume.HOME, Volume.COURSE_SHARE, Volume.COURSE_WORKDIR, Volume.COURSE_ASSIGNMENTDIR ]:
            try:
                volume = Volume.lookup(key)
                binding = VolumeCourseBinding.objects.create(course = instance, volume = volume)
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
    return
#FIXME:
    bindings = list(UserCourseBinding.objects.filter(user = user))
    for newbinding in newbindings:
        course = newbinding['course']
        #flag = newbinding['flag']
        is_teacher = newbinding['is_teacher']
        try:
            binding = UserCourseBinding.objects.get(user = user, course = course, is_teacher = is_teacher)
            if binding in bindings:
                bindings.remove(binding)
            continue
        except UserCourseBinding.DoesNotExist:
            UserCourseBinding.objects.create(user = user, course = course, is_teacher = is_teacher)
            logger.info("User %s binds to course %s/%s (is teacher: %s)" % (user, course, is_teacher))
    for binding in bindings:
        if binding.is_protected:
            logger.warn("According to IDP user %s is not bound to course %s any longer. Binding is not removed because it is protected" % (user, binding.course))
        else:
            logger.info("User %s is not bound to course %s any longer" % (user, binding.course))
            binding.delete()

