import os

from django.db import models
from time import strftime, localtime

from .project import Project, UserProjectBinding
from .scope import ScopeType
from .user import User
from .image import Image

from kooplex.lib import get_settings, standardize_str

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
        return "%s [%s %s]" % (self.notebook_filename, self.creator, self.project.name_with_owner)

    def __lt__(self, r):
        assert isinstance(r, Report)
        return self.ts_created > r.ts_created

    @property
    def pretty_ts(self):
        return strftime("%Y. %m. %d.", localtime(self.ts_created))

    def is_user_allowed(self, user):
        internal = ScopeType.objects.get(name = 'internal')
        if self.creator == user:
            return True
        if self.scope == internal:
            for collaborator in project.collaborators:
                if collaborator == user:
                    return True
        return False

    @property
    def is_public(self):
        return self.scope == ScopeType.objects.get(name = 'public')

class HtmlReport(Report):
    @property
    def displaytype(self):
        return 'Html report'

    @property
    def basepath(self):
        return os.path.join(get_settings('volumes', 'htmlreport'), self.creator.username, self.project.name_with_owner, str(self.ts_created))

    @property
    def filename_report_html(self):
        fn_wo_ext, _ = os.path.splitext(os.path.basename(self.notebook_filename))
        return os.path.join(get_settings('volumes', 'htmlreport'), self.creator.username, self.project.name_with_owner, str(self.ts_created), fn_wo_ext + '.html')

class DashboardReport(Report):
    image = models.ForeignKey(Image, null = False)
    notebook_dirname = models.CharField(max_length = 200, null = True)

    @property
    def displaytype(self):
        return 'Dashboard report'

    @property
    def report_dir(self):
        return "%s-%s-%s.%f" % (self.creator.username, self.project.name_with_owner, standardize_str(self.name), self.ts_created)

    @property
    def report_root(self):
        return os.path.join(get_settings('volumes', 'dashboardreport'), self.report_dir)

    @property
    def nb_path(self):
        return os.path.join(self.notebook_dirname, self.notebook_filename)

    def save(self):
        if hasattr(self, 'volname'):
            # make sure the current image is saved with the model
            self.image = self.project.image
            if self.volname == 'home':
                self.notebook_dirname = ""
            elif self.volname == 'git':
                self.notebook_dirname = "git"
            elif self.volname == 'share':
                self.notebook_dirname = "share"
        Report.save(self)      #FIXME: use the super() syntax

def _groupby(reports):
    reports_grouped = {}
    for r in reports:
        k = r.project, r.name
        if not k in reports_grouped:
            reports_grouped[k] = []
        reports_grouped[k].append(r)
    for rl in reports_grouped.values():
        rl.sort()
    return reports_grouped

def _list_user_reports(user):
    for report in HtmlReport.objects.filter(creator = user):
        report.ask_password = False
        report.is_configurable = True
        yield report
    for report in DashboardReport.objects.filter(creator = user):
        report.ask_password = False
        report.is_configurable = True
        yield report

def list_user_reports(user):
    return _groupby(_list_user_reports(user))

def _list_internal_reports(user):
    internal = ScopeType.objects.get(name = 'internal')
    for upb in UserProjectBinding.objects.filter(user = user):
        for report in HtmlReport.objects.filter(project = upb.project, scope = internal):
            if report.owner == user:
                continue
            report.ask_password = False
            report.is_configurable = False
            yield report
        for report in DashboardReport.objects.filter(project = upb.project, scope = internal):
            if report.owner == user:
                continue
            report.ask_password = False
            report.is_configurable = False
            yield report

def list_internal_reports(user):
    return _groupby(_list_internal_reports(user))

def _list_public_reports(authorized):
    public = ScopeType.objects.get(name = 'public')
    for report in HtmlReport.objects.filter(scope = public):
        report.ask_password = False if authorized or (len(report.password) == 0) else True
        report.is_configurable = False
        yield report
    for report in DashboardReport.objects.filter(scope = public):
        report.ask_password = False # Note: password is asked by the notebook server
        report.is_configurable = False
        yield report

def list_public_reports(authorized):
    return _groupby(_list_public_reports(authorized))

def get_report(**kw):
    try:
        return HtmlReport.objects.get(**kw)
    except HtmlReport.DoesNotExist:
        pass
    try:
        return DashboardReport.objects.get(**kw)
    except DashboardReport.DoesNotExist:
        pass
    raise ReportDoesNotExist("Cannot find either Html not Dashboard reports")

def filter_report(**kw):
    for report in HtmlReport.objects.filter(**kw):
        yield report
    for report in DashboardReport.objects.filter(**kw):
        yield report

