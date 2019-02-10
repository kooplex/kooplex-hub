import os
import logging

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str

logger = logging.getLogger(__name__)

class Dirname:
    mountpoint = KOOPLEX.get('mountpoint', {})

    @staticmethod
    def userhome(user):
        return os.path.join(Dirname.mountpoint['home'], user.username)

    @staticmethod
    def usergarbage(user):
        return os.path.join(Dirname.mountpoint['garbage'], user.username)

    @staticmethod
    def reportroot(user):
        return os.path.join(Dirname.mountpoint['report'], user.username)

    @staticmethod
    def reportprepare(user):
        return os.path.join(Dirname.reportroot(user), '_prepare')

    @staticmethod
    def report(report):
        return os.path.join(Dirname.reportroot(report.creator), standardize_str(report.name), report.created_at.strftime('%Y_%m_%d-%H:%M:%S'))

    @staticmethod
    def share(userprojectbinding):
        return os.path.join(Dirname.mountpoint['share'], userprojectbinding.project.uniquename)

    @staticmethod
    def workdir(userprojectbinding):
        return os.path.join(Dirname.mountpoint['workdir'], userprojectbinding.uniquename)

    @staticmethod
    def vcpcache(vcproject):
        return os.path.join(Dirname.mountpoint['git'], vcproject.uniquename)

    @staticmethod
    def course(course):
        return os.path.join(Dirname.mountpoint['course'], course.folder)

    @staticmethod
    def courseprivate(course):
        return os.path.join(Dirname.course(course), 'private')

    @staticmethod
    def coursepublic(course):
        return os.path.join(Dirname.course(course), 'public')

    @staticmethod
    def courseworkdir(usercoursebinding):
        return os.path.join(Dirname.mountpoint['usercourse'], usercoursebinding.course.folder)

    @staticmethod
    def usercourseworkdir(usercoursebinding):
        return os.path.join(Dirname.courseworkdir(usercoursebinding), usercoursebinding.user.username)

    @staticmethod
    def assignmentsource(assignment):
        return os.path.join(Dirname.courseprivate(assignment.coursecode.course), assignment.folder)

    @staticmethod
    def assignmentworkdir(userassignmentbinding):
        from hub.models import UserCourseBinding
        usercoursebinding = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.coursecode.course)
        wd = Dirname.usercourseworkdir(usercoursebinding)
        return os.path.join(wd, userassignmentbinding.assignment.safename)

    @staticmethod
    def assignmentcorrectdir(userassignmentbinding):
        assignment = userassignmentbinding.assignment
        user = userassignmentbinding.user
        namefield = "%s%s_%s" % (user.first_name, user.last_name, user.username)
        datefield = userassignmentbinding.submitted_at.strftime('%Y_%m_%d')
        return os.path.join(Dirname.mountpoint['assignment'], assignment.coursecode.course.folder, 'feedback-%s-%s-%s' % (assignment.safename, namefield, datefield))


    @staticmethod
    def containervolume_listfolders(container, volume):
        from hub.models import UserCourseBinding, UserAssignmentBinding
        def get_usercoursebinding_userstate():
            try:
                usercoursebinding = UserCourseBinding.objects.get(user = container.user, course = container.course)
            except UserCourseBinding.DoesNotExist:
                logger.error("Silly situation, cannot map %s %s COZ user course binding instance is missing" % (volume, container))
                return None, None
            if container.course in container.user.profile.courses_taught():
                return usercoursebinding, 'teacher'
            elif container.course in container.user.profile.courses_attend():
                return usercoursebinding, 'student'
            else:
                logger.error("Silly situation, cannot map %s %s" % (volume, container))
                return None, None

        if volume.volumetype == volume.HOME:
            yield Dirname.userhome(container.user)
        elif volume.volumetype == volume.GARBAGE:
            yield Dirname.usergarbage(container.user)
        elif volume.volumetype == volume.SHARE:
            for upb in container.userprojectbindings:
                yield Dirname.share(upb)
        elif volume.volumetype == volume.WORKDIR:
            for upb in container.userprojectbindings:
                yield Dirname.workdir(upb)
        elif volume.volumetype == volume.GIT:
            for vcppb in container.vcprojectprojectbindings:
                yield Dirname.vcpcache(vcppb.vcproject)
        elif volume.volumetype == volume.COURSE_SHARE:
            if container.course in container.user.profile.courses_taught():
                yield Dirname.course(container.course)
            elif container.course in container.user.profile.courses_attend():
                yield Dirname.coursepublic(container.course)
            else:
                logger.error("Silly situation, cannot map %s %s" % (volume, container))
        elif volume.volumetype == volume.COURSE_WORKDIR and container.course:
            usercoursebinding, userstatus = get_usercoursebinding_userstate()
            if userstatus == 'teacher':
                yield Dirname.courseworkdir(usercoursebinding)
            elif userstatus == 'student':
                yield Dirname.usercourseworkdir(usercoursebinding)
            else:
                yield "OOPS_%s" % volume.volumetype
        elif volume.volumetype == volume.COURSE_ASSIGNMENTDIR and container.course:
            _, userstatus = get_usercoursebinding_userstate()
            if userstatus == 'teacher':
                for binding in UserAssignmentBinding.objects.all():
                    if binding.state == UserAssignmentBinding.ST_QUEUED or binding.corrector is None or binding.assignment.coursecode.course != container.course:
                        continue
                    yield Dirname.assignmentcorrectdir(binding)
            elif userstatus == 'student':
                for binding in UserAssignmentBinding.objects.filter(user = container.user):
                    if binding.state == UserAssignmentBinding.ST_QUEUED or binding.corrector is None or binding.assignment.coursecode.course != container.course:
                        continue
                    yield Dirname.assignmentcorrectdir(binding)
            else:
                yield "OOPS_%s" % volume.volumetype
        elif volume.volumetype == volume.REPORT:
            yield Dirname.reportroot(container.user)
        else:
            yield "MISSING_DIRNAME_%s" % volume.volumetype


