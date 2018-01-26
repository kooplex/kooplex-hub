import os
from django.db import models
from django.utils import timezone

from kooplex.lib import get_settings

from .user import User
from .project import Project
from .volume import Volume, VolumeProjectBinding
from .image import Image

class Container(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 200, null = True)
    user = models.ForeignKey(User, null = True)
    image = models.ForeignKey(Image, null = True)
    launched_at = models.DateTimeField(default = timezone.now)
    is_running = models.BooleanField(default = False)

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    @property
    def volumes(self):
        from .volume import lookup
        for vcb in VolumeContainerBinding.objects.filter(container = self):
            yield lookup( vcb.volume )

class ProjectContainer(Container):
    project = models.ForeignKey(Project, null = True)
    mark_to_remove = models.BooleanField(default = False)

    def __str__(self):
        return "<ProjectContainer: %s of %s@%s>" % (self.name, self.user, self.project)

    def init(self):
        container_name_info = { 'username': self.user.username, 'projectname': self.project.name_with_owner }
        self.name = get_settings('spawner', 'pattern_project_containername') % container_name_info
        self.image = self.project.image
        for vpb in VolumeProjectBinding.objects.filter(project = self.project):
            vcb = VolumeContainerBinding(container = self, volume = vpb.volume)
            vcb.save()

    @property
    def proxy_path(self):
        info = { 'containername': self.name }
        return get_settings('spawner', 'pattern_proxypath') % info

    @property
    def url(self):
        return "http://%s:%d" % (self.name, 8000) #FIXME: PORT hardcoded

    @property
    def url_with_token(self):
        return os.path.join(get_settings('hub', 'base_url'), self.proxy_path, '?token=%s' % self.user.token)

    @property
    def volumemapping(self):
        return [
            (get_settings('spawner', 'volume-home'), '/mnt/.volumes/home', 'rw'),
            (get_settings('spawner', 'volume-git'), '/mnt/.volumes/git', 'rw'),
            (get_settings('spawner', 'volume-share'), '/mnt/.volumes/share', 'rw'),
        ]

    @property
    def environment(self):
        return {
            'NB_USER': self.user.username,
            'NB_UID': self.user.uid,
            'NB_GID': self.user.gid,
            'NB_URL': self.proxy_path,
            'NB_PORT': 8000,
            'NB_TOKEN': self.user.token,
            'PR_ID': self.project.id,
            'PR_NAME': self.project.name,
            'PR_PWN': self.project.name_with_owner,
        }

    @property
    def command(self):
        return get_settings('spawner', 'nbcommand')


class DashboardContainer(Container):
    from .report import DashboardReport
    report = models.ForeignKey(DashboardReport, null = True)

    def __str__(self):
        return "<DashboardContainer: %s of %s@%s>" % (self.name, self.user, self.report)

    def init(self, container):
        raise NotImplementedError
        dashboardlimit = get_settings('spawner', 'max_dashboards_per_report')
        dashboard_containers = DashboardContainer.objects.filter(report = self.report)
        if len(dashboard_containers) >= dashboardlimit:
            logger.warning("%s dashboard report reached the limits of %d containers" % (report, dashboardlimit))
            self.delete()
            raise Exception("cannot launch more dashboard containers for this project")
#FIXME: calculate instance_id
        container_name_info = { 'instance_id': TBD, 'reportname': self.report.name }
        self.name = get_settings('spawner', 'pattern_dashboard_containername') % container_name_info
        self.image = self.report.project.image
        for vpb in VolumeProjectBinding.objects.filter(project = self.report.project):
            vcb = VolumeContainerBinding(container = self, volume = vpb.volume)
            vcb.save()

    @property
    def proxy_path(self):
        raise NotImplementedError

    @property
    def url(self):
        raise NotImplementedError

    @property
    def volumemapping(self):
        return [
            (get_settings('volumes', 'dashboardreport'), '/mnt/.volumes/reports', 'ro'),
        ]

    @property
    def environment(self):
        raise NotImplementedError

    @property
    def command(self):
        return get_settings('spawner', 'dbcommand')


class VolumeContainerBinding(models.Model):
    id = models.AutoField(primary_key = True)
    volume = models.ForeignKey(Volume, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
       return "%s-%s" % (self.container.name, self.volume.name)

