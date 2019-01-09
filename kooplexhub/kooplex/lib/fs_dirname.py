import os

from kooplex.settings import KOOPLEX

class Dirname:
    #from hub.models import Volume
    mountpoint = KOOPLEX.get('mountpoint', {})

    @staticmethod
    def userhome(user):
        return os.path.join(Dirname.mountpoint['home'], user.username)

    @staticmethod
    def share(userprojectbinding):
    #    v_share = Volume.objects.get(volumetype = Volume.SHARE['tag'])
    #    return os.path.join(v_share.mountpoint, userprojectbinding.uniquename)
        v_share = Dirname.mountpoint['share']
        return os.path.join(v_share, userprojectbinding.project.uniquename)

    @staticmethod
    def workdir(userprojectbinding):
    #    v_workdir = Volume.objects.get(volumetype = Volume.WORKDIR['tag'])
    #    return os.path.join(v_workdir.mountpoint, self.uniquename)
        v_workdir = Dirname.mountpoint['workdir']
        return os.path.join(v_workdir, userprojectbinding.uniquename)

    @staticmethod
    def vcpcache(vcprojectprojectbinding):
        v_vccache = Dirname.mountpoint['git']
        return os.path.join(v_vccache, vcprojectprojectbinding.uniquename)

    @staticmethod
    def course(course):
        return os.path.join(Dirname.mountpoint['course'], course.safecourseid)

    @staticmethod
    def courseprivate(course):
        return os.path.join(Dirname.course(course), 'private')

    @staticmethod
    def coursepublic(course):
        return os.path.join(Dirname.course(course), 'public')

    @staticmethod
    def courseworkdir(usercoursebinding):
        flag = usercoursebinding.flag if usercoursebinding.flag else '_'
        return os.path.join(Dirname.mountpoint['usercourse'], usercoursebinding.course.safecourseid, flag) if usercoursebinding.is_teacher else \
               os.path.join(Dirname.mountpoint['usercourse'], usercoursebinding.course.safecourseid, flag, usercoursebinding.user.username)

    @staticmethod
    def assignmentsource(assignment):
        return os.path.join(Dirname.courseprivate(assignment.course), assignment.folder)

    @staticmethod
    def assignmentworkdir(userassignmentbinding):
        from hub.models import UserCourseBinding
        usercoursebinding = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course, flag = userassignmentbinding.assignment.flag)
        wd = Dirname.courseworkdir(usercoursebinding)
        return os.path.join(wd, userassignmentbinding.assignment.safename)

    @staticmethod
    def assignmentcorrectdir(userassignmentbinding):
        assignment = userassignmentbinding.assignment
        flag = assignment.flag if assignment.flag else '_'
        return os.path.join(Dirname.mountpoint['assignment'], assignment.course.safecourseid, flag, 'feedback-%s-%s.%d' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp()))
