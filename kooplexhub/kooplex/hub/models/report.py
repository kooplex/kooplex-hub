import os.path
import json
from django.db import models
from django.core.urlresolvers import reverse
from shutil import copyfile as cp
from os import mkdir
from distutils import dir_util, file_util
from time import time, strftime, localtime

from .project import Project, UserProjectBinding
from .scope import ScopeType
from .user import User
from .image import Image

from kooplex.lib import get_settings

class ReportDoesNotExist(Exception):
    pass

class Report(models.Model):
    id = models.AutoField(primary_key = True)
    creator = models.ForeignKey(User, null = False)
    name = models.CharField(max_length = 200, null = True)
    description = models.TextField(null=True)
    ts_created = models.IntegerField(null = True)
    project = models.ForeignKey(Project, null = False)
    notebook_filename = models.CharField(max_length = 200, null = True)
    scope = models.ForeignKey(ScopeType, null = False)
    password = models.CharField(max_length = 128, null = True)  #TODO: may store encrypted

    def __str__(self):
        return "%s [%s]" % (self.filename_wo_ext, self.project.name_with_owner)

    def __lt__(self, r):
        assert isinstance(r, Report)
        return self.ts_created > r.ts_created

    @property
    def pretty_ts(self):
        return strftime("%Y %m. %d.", localtime(self.ts_created))

    @property
    def filename_wo_ext(self):
        fn_wo_ext, _ = os.path.splitext(os.path.basename(self.notebook_filename))
        return fn_wo_ext

    def is_user_allowed(self, user):
        public = ScopeType.objects.get(name = 'public')
        internal = ScopeType.objects.get(name = 'internal')
        if self.scope == public:
            return True
        if self.creator == user:
            return True
        if self.scope == internal:
            for collaborator in project.collaborators:
                if collaborator == user:
                    return True
        return False

class HtmlReport(Report):
    @property
    def displaytype(self):
        return 'Html report'

    @property
    def filename(self): #FIXME: rename it
        # as the user sees in their container
        mp_home = get_settings('volumes', 'home')
        mp_share = get_settings('volumes', 'share')
        mp_git = get_settings('volumes', 'git')
        if self.notebook_filename.startswith(mp_home):
            return '/home' + self.notebook_filename[len(mp_home):]
        if self.notebook_filename.startswith(mp_git):
            wd_hub = os.path.join(mp_git, self.creator.username, self.project.name_with_owner)
            wd_usercontainer = os.path.join('/home', self.creator.username, 'git')
            return self.notebook_filename.replace(wd_hub, wd_usercontainer)
        if self.notebook_filename.startswith(mp_share):
            wd_hub = os.path.join(mp_share, self.project.name_with_owner)
            wd_usercontainer = os.path.join('/home', self.creator.username, 'share')
            return self.notebook_filename.replace(wd_hub, wd_usercontainer)
        else:
            raise NotImplementedError

    @property
    def filename_html(self):
        fn_wo_ext, _ = os.path.splitext(self.notebook_filename)
        return fn_wo_ext + '.html'

    @property
    def filename_report_html(self):
        return os.path.join(get_settings('volumes', 'htmlreport'), self.creator.username, self.project.name_with_owner, str(self.ts_created), self.filename_wo_ext + '.html')

class DashboardReport(Report):
    image = models.ForeignKey(Image, null = False)

    @property
    def displaytype(self):
        return 'Dashboard report'

    @property
    def report_root(self):
        return os.path.join(get_settings('volumes', 'dashboardreport'), "%s-%s-%s.%f" % (self.creator.username, self.project.name_with_owner, self.name, self.ts_created))

    def save(self):
        # make sure the current image is saved with the model
        self.image = self.project.image
        Report.save(self)

def list_user_reports(user):
    for report in HtmlReport.objects.filter(creator = user):
        yield report
    for report in DashboardReport.objects.filter(creator = user):
        yield report

def list_internal_reports(user):
    internal = ScopeType.objects.get(name = 'internal')
    for upb in UserProjectBinding.objects.filter(user = user):
        for report in HtmlReport.objects.filter(project = upb.project, scope = internal):
            if report.owner == user:
                continue
            yield report
        for report in DashboardReport.objects.filter(project = upb.project, scope = internal):
            if report.owner == user:
                continue
            yield report

def list_public_reports():
    public = ScopeType.objects.get(name = 'public')
    for report in HtmlReport.objects.filter(scope = public):
        yield report
    for report in DashboardReport.objects.filter(scope = public):
        yield report

def get_report(**kw):
    try:
        return HtmlReport.objects.get(**kw)
    except:
        pass
    try:
        return DashboardReport.objects.get(**kw)
    except:
        pass
    raise ReportDoesNotExist("Cannot find either Html not Dashboard reports")

