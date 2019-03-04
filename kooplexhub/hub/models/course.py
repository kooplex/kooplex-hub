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
    name = models.CharField(max_length = 64, null = False)
    folder = models.CharField(max_length = 64, null = False)
    description = models.TextField(max_length = 512, blank = True)
    image = models.ForeignKey(Image, null = True)

    def __str__(self):
        #return "Course: %s" % self.name #FIXME: OperationalError at /admin/hub/course/31/change/ (1366, "Incorrect string value: '\\xC5\\xB1s\\xC3\\xA9g...' for column 'object_repr' at row 1")
        return "Course: {}".format(self.name)

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
            yield coursecode
            #try:
            #    UserCourseCodeBinding.objects.get(user = user, coursecode = coursecode)
            #    yield coursecode
            #except UserCourseCodeBinding.DoesNotExist:
            #    pass

    @register.filter
    def coursecodes_joined(self, user):
        return ", ".join([ c.courseid for c in self.coursecodes(user) ])

    def count_coursecodestudents(self, coursecode):
        assert coursecode.course == self, "Coursecode mssmatch %s and %s" % (self, coursecode)
        return len(UserCourseCodeBinding.objects.filter(coursecode = coursecode, is_teacher = False))

    @register.filter
    def lookup_userassignmentbindings(self, student):
        from .assignment import Assignment, UserAssignmentBinding
#FIXME
        assignments = list(Assignment.objects.filter(course = self))
        for binding in UserAssignmentBinding.objects.filter(user = student):
            if binding.assignment in assignments:
                yield binding



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
            f = os.path.join(dir_courseprivate, d)
            if os.path.isdir(f):
                if len(os.listdir(f) ) > 0:
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

    def userassignmentbindings(self, **kw):
        from .assignment import Assignment, UserAssignmentBinding
        s_a = kw.pop('s_assignment', None)
        s_n = kw.pop('s_name', None)
        s_u = kw.pop('s_username', None)
        s_s = kw.pop('s_assignmentstate', None)
        user = kw.pop('user', None)
        for coursecode in CourseCode.objects.filter(course = self):
            for assignment in Assignment.objects.filter(coursecode = coursecode):
                query = models.Q(assignment = assignment)
                if user is not None:
                    query &= models.Q(user = user)
                if s_s is not None:
                    query &= models.Q(state = s_s)
                if s_a is not None:
                    query &= models.Q(assignment__name__icontains = s_a)
                if s_n is not None:
                    query &= models.Q(user__first_name__icontains = s_n) | models.Q(user__last_name__icontains = s_n)
                if s_u is not None:
                    query &= models.Q(user__username__icontains = s_u)
                for binding in UserAssignmentBinding.objects.filter(query):
                    yield binding


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

    @staticmethod
    def parse(attributelist):
        coursecodes = []
        for courseid in attributelist:
            #courseid = standardize_str(courseid)
            try:
                coursecode = CourseCode.objects.get(courseid = courseid)
            except CourseCode.DoesNotExist:
                coursecode = CourseCode.objects.create(courseid = courseid)
                logger.info('New coursecode %s' % (coursecode))
            coursecodes.append(coursecode)
        return coursecodes


class UserCourseCodeBinding(models.Model):
    user = models.ForeignKey(User, null = False)
    coursecode = models.ForeignKey(CourseCode, null = False)
    is_teacher = models.BooleanField(default = False)
    is_protected = models.BooleanField(default = False)

    def __str__(self):
        return "%s code: %s, teacher: %s" % (self.user, self.coursecode, self.is_teacher)

    @staticmethod
    def userattributes(user, coursecodes, is_teacher):
        former_bindings = [ b for b in UserCourseCodeBinding.objects.filter(user = user, is_teacher = is_teacher, is_protected = False) ]
        logger.debug('%s has %d former unprotected bindings' % (user, len(former_bindings)))
        for coursecode in coursecodes:
            try:
                binding = UserCourseCodeBinding.objects.get(user = user, coursecode = coursecode, is_teacher = is_teacher)
                former_bindings.remove(binding)
            except UserCourseCodeBinding.DoesNotExist:
                binding = UserCourseCodeBinding.objects.create(user = user, coursecode = coursecode, is_teacher = is_teacher)
                logger.info('New usercoursecodebinding %s' % (binding))
            except ValueError:
                # protected bindings not in former_bindings
                pass
        for binding in former_bindings:
            logger.info('Removing usercoursecodebinding %s' % (binding))
            binding.delete()


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





@receiver(pre_save, sender = CourseCode)
def manage_usercoursebindings(sender, instance, **kwargs):
    if instance.course is None:
        return
    is_new = instance.id is None
    if not is_new:
        old = CourseCode.objects.get(id = instance.id)
        if old.course == instance.course:
            return
        for b in UserCourseCodeBinding.objects.filter(coursecode = instance):
            for binding in UserCourseBinding.objects.filter(user = b.user, course = old.course):
                binding.delete()
                logger.info('Delete binding %s (remapped coursecode %s %s -> %s' % (binding, instance, old.course, instance.course))
    for b in UserCourseCodeBinding.objects.filter(coursecode = instance):
        binding, created = UserCourseBinding.objects.get_or_create(user = b.user, course = instance.course, is_teacher = b.is_teacher, is_protected = b.is_protected)
        if created:
            logger.info('New binding %s' % binding)




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


@receiver(pre_save, sender = Course)
def mkdir_course(sender, instance, **kwargs):
    from kooplex.lib.filesystem import mkdir_course_share
    from kooplex.lib.fs_dirname import Dirname
    instance.folder = standardize_str(instance.folder)
    c_ids = [ c.id for c in Course.objects.filter(folder = instance.folder) ]
    if len(c_ids) == 1:
        c_id = c_ids.pop()
        assert c_id == instance.id, "Folder name %s is already taken" % instance.folder
    assert len(c_ids) == 0, "Folder name %s is already taken" % instance.folder
    c_ids = [ c.id for c in Course.objects.filter(folder = instance.folder) ]
    if len(c_ids) == 1:
        c_id = c_ids.pop()
        assert c_id == instance.id, "Folder name %s is already taken" % instance.folder
    assert len(c_ids) == 0, "Folder name %s is already taken" % instance.folder
    is_new = instance.id is None
    if is_new:
        mkdir_course_share(instance)
    else:
        old = Course.objects.get(id = instance.id)
        f_o = Dirname.course(old)
        f_n = Dirname.course(instance)
        try:
            os.rename(f_o, f_n)
            logger.info("%s folder rename %s -> %s" % (instance, f_o, f_n))
        except Exception as e:
            logger.warning("failed to rename %s folder rename %s -> %s -- %s" % (instance, f_o, f_n, e))
        for b in UserCourseBinding.objects.filter(course = old):
            f_o = Dirname.courseworkdir(b)
            b_ = UserCourseBinding(course = instance, user = b.user)
            f_n = Dirname.courseworkdir(b_)
            try:
                os.rename(f_o, f_n)
                logger.info("%s folder rename %s -> %s" % (instance, f_o, f_n))
            except Exception as e:
                logger.warning("failed to rename %s folder rename %s -> %s -- %s" % (instance, f_o, f_n, e))


@receiver(post_delete, sender = Course)
def garbagedir_course(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbagedir_course_share, rmdir_course_workdir
    garbagedir_course_share(instance)
    rmdir_course_workdir(instance)


@receiver(post_save, sender = UserCourseBinding)
def mkdir_usercourse(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import mkdir_course_workdir, grantacl_course_workdir, grantacl_course_share
    if created:
        grantacl_course_share(instance)
        mkdir_course_workdir(instance)
        grantacl_course_workdir(instance)
        if instance.is_teacher == False:
            for binding in UserCourseBinding.objects.filter(course = instance.course, is_teacher = True):
                grantacl_course_workdir(binding)


@receiver(pre_delete, sender = UserCourseBinding)
def movedir_usercourse(sender, instance, **kwargs):
    from kooplex.lib.filesystem import archive_course_workdir, revokeacl_course_workdir, revokeacl_course_share
    archive_course_workdir(instance)
    revokeacl_course_workdir(instance)
    revokeacl_course_share(instance)




