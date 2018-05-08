from django.db import models

from kooplex.lib import get_settings, standardize_str

from .user import User
from .image import Image
from .scope import ScopeType

class Project(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.TextField(max_length = 200, null = False)
    description = models.TextField(null=True)
    owner = models.ForeignKey(User, null = True)
    image = models.ForeignKey(Image, null = True)
    scope = models.ForeignKey(ScopeType, null = True)
    gitlab_id = models.IntegerField(null = True)

    _collaborators = None
    _volumes = None

    def __lt__(self, p):
        return self.name < p.name

    def __str__(self):
        return "%s@%s" % (self.name, self.owner)

    @property
    def name_with_owner(self):
        return "%s-%s" % (standardize_str(self.name), self.owner.username)

    @property
    def gitlabname(self):
        return standardize_str(self.name)

    @property
    def collaborators(self):
        if self._collaborators is None:
            self._collaborators = UserProjectBinding.objects.filter(project = self)
        for upb in self._collaborators:
            yield upb.user

    @property
    def volumes(self):
        from .volume import VolumeProjectBinding, lookup
        if self._volumes is None:
            self._volumes = VolumeProjectBinding.objects.filter(project = self)
        for vpb in self._volumes:
            yield lookup( vpb.volume )

    @property
    def url_gitlab(self):
        info = {
            'username': self.owner.username,
            'projectname': self.gitlabname,
        }
        return get_settings('gitlab', 'pattern_urlproject') % info

    @property
    def reports(self):
        from .report import HtmlReport, DashboardReport
        for report in HtmlReport.objects.filter(project = self):
            yield report
        for report in DashboardReport.objects.filter(project = self):
            yield report

    @property
    def containers(self):
        from .container import ProjectContainer
        return ProjectContainer.objects.filter(project = self)

class UserProjectBinding(models.Model):
    id = models.AutoField(primary_key = True)
    user = models.ForeignKey(User, null = False)
    project = models.ForeignKey(Project, null = False)

    def __str__(self):
       return "%s-%s" % (self.project.name, self.user.username)


def get_project(**kw):
    try:
        return Project.objects.get(**kw)
    except Project.DoesNotExist:
        if not 'name' in kw:
            raise
        project_name = kw.pop('name')
        filterprojects_pre = Project.objects.filter(**kw)
        filterprojects_fin = []
        for p in filterprojects_pre:
            if p.gitlabname == project_name:
                filterprojects_fin.append(p)
        if len(filterprojects_fin) == 1:
            return filterprojects_fin[0]
        raise

