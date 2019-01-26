import os

from kooplex.settings import KOOPLEX

class Dirname:
    mountpoint = KOOPLEX.get('mountpoint', {})

    @staticmethod
    def userhome(user):
        return os.path.join(Dirname.mountpoint['home'], user.username)

    @staticmethod
    def share(userprojectbinding):
        v_share = Dirname.mountpoint['share']
        return os.path.join(v_share, userprojectbinding.project.uniquename)

    @staticmethod
    def workdir(userprojectbinding):
        v_workdir = Dirname.mountpoint['workdir']
        return os.path.join(v_workdir, userprojectbinding.uniquename)

    @staticmethod
    def vcpcache(vcproject):
        v_vccache = Dirname.mountpoint['git']
        return os.path.join(v_vccache, vcproject.uniquename)

    @staticmethod
    def course(course):
        return os.path.join(Dirname.mountpoint['course'], course.safename)

    @staticmethod
    def courseprivate(course):
        return os.path.join(Dirname.course(course), 'private')

    @staticmethod
    def coursepublic(course):
        return os.path.join(Dirname.course(course), 'public')

    @staticmethod
    def courseworkdir(usercoursebinding):
        return os.path.join(Dirname.mountpoint['usercourse'], usercoursebinding.course.safename)

    @staticmethod
    def usercourseworkdir(usercoursebinding):
        return os.path.join(Dirname.courseworkdir(usercoursebinding), usercoursebinding.user.username)

    @staticmethod
    def assignmentsource(assignment):
        return os.path.join(Dirname.courseprivate(assignment.coursecode.course), assignment.folder)


    @staticmethod
    def containervolume_listfolders(container, volume):
        from hub.models import UserCourseBinding
        if volume.volumetype == volume.HOME['tag']:
            yield Dirname.userhome(container.user)
        elif volume.volumetype == volume.SHARE['tag']:
            for upb in container.userprojectbindings:
                yield Dirname.share(upb)
        elif volume.volumetype == volume.WORKDIR['tag']:
            for upb in container.userprojectbindings:
                yield Dirname.workdir(upb)
        elif volume.volumetype == volume.GIT['tag']:
            for vcppb in container.vcprojectprojectbindings:
                yield Dirname.vcpcache(vcppb.vcproject)
        elif volume.volumetype == volume.COURSE_SHARE['tag']:
            if container.course in container.user.profile.courses_taught():
                yield Dirname.course(container.course)
            elif container.course in container.user.profile.courses_attend():
                yield Dirname.coursepublic(container.course)
            else:
                logger.error("Silly situation, cannot map %s %s" % (volume, container))
        elif volume.volumetype == volume.COURSE_WORKDIR['tag']:
            try:
                usercoursebinding = UserCourseBinding.objects.get(user = container.user, course = container.course)
            except UserCourseBinding.DoesNotExist:
                logger.error("Silly situation, cannot map %s %s COZ user course binding instance is missing" % (volume, container))
            if container.course in container.user.profile.courses_taught():
                yield Dirname.courseworkdir(usercoursebinding)
            elif container.course in container.user.profile.courses_attend():
                yield Dirname.usercourseworkdir(usercoursebinding)
            else:
                logger.error("Silly situation, cannot map %s %s" % (volume, container))
        elif volume.volumetype == volume.COURSE_ASSIGNMENTDIR['tag']:
            yield "FIXME" #Dirname.courseworkdir(container.course)
        else:
            raise NotImplementedError("DIRNAME %s" % volume.volumetype)


    @staticmethod
    def assignmentworkdir(userassignmentbinding):
        from hub.models import UserCourseBinding
        usercoursebinding = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.courseid.course)
        wd = Dirname.courseworkdir(usercoursebinding)
        return os.path.join(wd, userassignmentbinding.assignment.safename)

    @staticmethod
    def assignmentcorrectdir(userassignmentbinding):
        assignment = userassignmentbinding.assignment
        flag = assignment.flag if assignment.flag else '_'
        return os.path.join(Dirname.mountpoint['assignment'], assignment.coursecode.course.safename, 'feedback-%s-%s.%d' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp()))
