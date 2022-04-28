import os
import logging
import unidecode
from pwd import getpwnam

from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    token = models.CharField(max_length = 64, null = True)
    can_createproject = models.BooleanField(default = True)
    can_createimage = models.BooleanField(default = False)
    can_createattachment = models.BooleanField(default = False)
    can_runjob = models.BooleanField(default = False)
    has_scratch = models.BooleanField(default = False)

    search_project_list = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_project_join = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_project_showhide = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_project_collaborator = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_project_container = models.CharField(max_length = 30, blank = True, null = True, default = "")

    search_education_student = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_education_teacher = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_education_assignment_config = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_education_assignment_mass = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_education_assignment_individual = models.CharField(max_length = 30, blank = True, null = True, default = "")

    search_container_list = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_container_projects = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_container_library = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_container_repository = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_container_attachments = models.CharField(max_length = 30, blank = True, null = True, default = "")

    search_attachment_list = models.CharField(max_length = 30, blank = True, null = True, default = "")

    search_report_list = models.CharField(max_length = 30, blank = True, null = True, default = "")

    search_external_library = models.CharField(max_length = 30, blank = True, null = True, default = "")
    search_external_repository = models.CharField(max_length = 30, blank = True, null = True, default = "")

    layout_project_list = models.BooleanField(default = True)
    layout_container_list = models.BooleanField(default = True)
    layout_report_list = models.BooleanField(default = True)

#deprecate    paginate_project_list = models.IntegerField(default = 16)
#    paginate_container_list = models.IntegerField(default = 16)
#    paginate_report_list = models.IntegerField(default = 16)

    @property
    def userid(self):
        if hasattr(self.user, 'is_superuser') and (self.user.is_superuser == True):
            return None
        return getpwnam(self.username).pw_uid

    @property
    def name(self):
        return '{} {}'.format(self.user.first_name, self.user.last_name)

    @property
    def username(self):
        return self.user.username

    @property
    def name_and_username(self):
        return f'{self.name} ({self.username})'

    @property
    def safename(self):
        return "%s_%s" % (unidecode.unidecode(self.user.last_name), unidecode.unidecode(self.user.first_name).replace(' ', ''))

    @property
    def everybodyelse(self):
        return Profile.objects.filter(~models.Q(id = self.id) & ~models.Q(user__is_superuser = True))

    def everybodyelse_like(self, pattern):
        return Profile.objects.filter(~models.Q(id = self.id) & ~models.Q(user__is_superuser = True) & (models.Q(user__username__icontains = pattern) | models.Q(user__first_name__icontains = pattern) | models.Q(user__last_name__icontains = pattern)))

    @property
    def projectbindings(self):
        from project.models import UserProjectBinding
        for binding in UserProjectBinding.objects.filter(user = self.user):
            yield binding

    @property
    def number_of_hidden_projects(self):
        return len(list(filter(lambda x: x.is_hidden, self.projectbindings)))

    @property
    def containers(self):
        from .container import Container
        for svc in Container.objects.filter(user = self.user):
             yield svc

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
             yield report.latest, T, report.subcategory_name
             reports_shown.update(set(g))

    def usercoursebindings(self, **kw):
        from education.models import UserCourseBinding
        return UserCourseBinding.objects.filter(user = self.user, **kw)

    @property
    def is_teacher(self):
        return len(self.usercoursebindings(is_teacher = True)) > 0

    def courses_taught(self):
        return [ binding.course for binding in self.usercoursebindings(is_teacher = True) ]

    @property
    def is_student(self):
        return len(self.usercoursebindings(is_teacher = False)) > 0

    def courses_attend(self):
        return [ binding.course for binding in self.usercoursebindings(is_teacher = False) ]

#FIXME    def is_coursecodeteacher(self, coursecode):
#FIXME        from .course import UserCourseCodeBinding
#FIXME        try:
#FIXME            UserCourseCodeBinding.objects.get(user = self.user, coursecode = coursecode, is_teacher = True)
#FIXME            return True
#FIXME        except UserCourseCodeBinding.DoesNotExist:
#FIXME            return False
#FIXME
#FIXME    @property
#FIXME    def courseprojects_attended(self): #FIXME
#FIXME        duplicate = set()
#FIXME        for coursebinding in self.coursebindings:
#FIXME            if not coursebinding.is_teacher:
#FIXME                if coursebinding.course.project in duplicate:
#FIXME                    continue
#FIXME                yield coursebinding.course.project
#FIXME                duplicate.add(coursebinding.course.project)
#FIXME
#FIXME    def projects_reportprepare(self):
#FIXME        for b in self.projectbindings:
#FIXME            yield (b.project.id, b.project.uniquename)
#FIXME
#FIXME    @sudo
#FIXME    def files_reportprepare(self):
#FIXME        tree = {}
#FIXME        for b in self.projectbindings:
#FIXME            report_dir = Dirname.reportprepare(b.project)
#FIXME            sub_tree = {}
#FIXME            for d in list(filter(lambda d: not d.startswith('.') and os.path.isdir(os.path.join(report_dir, d)), os.listdir(report_dir))):
#FIXME                files = list(filter(lambda f: f.endswith('.ipynb') or f.endswith('.html') or f.endswith('.py') or f.endswith('.R') or f.endswith('.r'), os.listdir( os.path.join(report_dir, d) )))
#FIXME                if len(files):
#FIXME                    sub_tree[d] = files
#FIXME            if len(sub_tree):
#FIXME                tree[b.project] = sub_tree
#FIXME        return tree
#FIXME
#FIXME    @property
#FIXME    def functional_volumes(self):
#FIXME        from .volume import Volume
#FIXME        for volume in Volume.filter(Volume.FUNCTIONAL):
#FIXME            yield volume
#FIXME
#FIXME    @property
#FIXME    def storage_volumes(self):
#FIXME        from .volume import Volume
#FIXME        for volume in Volume.filter(Volume.STORAGE, user = self.user):
#FIXME            yield volume

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


