import logging
import re
import os
from django.db import models
from django.utils import timezone

from kooplex.lib import get_settings, standardize_str

from .user import User
from .project import Project
from .volume import Volume, VolumeProjectBinding
from .image import Image

logger = logging.getLogger(__name__)

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
    def url(self):
        return "http://%s:%d" % (self.name, 8000) #FIXME: PORT hardcoded

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
        return get_settings('spawner', 'pattern_notebook_proxypath') % info

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


class LimitReached(Exception):
    pass

class DashboardContainer(Container):
    from .report import DashboardReport
    report = models.ForeignKey(DashboardReport, null = True)

    def __str__(self):
        return "<DashboardContainer: %s of %s@%s>" % (self.name, self.user, self.report)

    def init(self):
        dashboardlimit = get_settings('spawner', 'max_dashboards_per_report')
        dashboardnamefilter = get_settings('spawner', 'pattern_dashboard_containername_filter')
        pool = list(range(dashboardlimit))
        for dbc in DashboardContainer.objects.filter(report = self.report):
            if dbc.name is None:
                logger.warning("%s" % (dbc))
                continue
            _, _, used_id, _ = re.split(dashboardnamefilter, dbc.name)
            used_id = int(used_id)
            pool.remove(used_id)
            logger.debug("dashboard id %d for report %s is occupied" % (used_id, self.report))
        logger.debug("LEFT %d" % len(pool))
        if len(pool) == 0:
            logger.warning("%s dashboard report reached the limits of %d containers" % (self.report, dashboardlimit))
            self.delete()
            raise LimitReached("cannot launch more dashboard containers for report %s" % self.report)
        container_name_info = { 'instance_id': pool.pop(), 'reportname': standardize_str(self.report.name) }
        self.name = get_settings('spawner', 'pattern_dashboard_containername') % container_name_info
        self.image = self.report.project.image
        for vpb in VolumeProjectBinding.objects.filter(project = self.report.project):
            vcb = VolumeContainerBinding(container = self, volume = vpb.volume)
            vcb.save()
        self.save() #FIXME: breaks symmetry

    @property
    def proxy_path(self):
        info = { 'containername': self.name, 'notebook_file': self.report.notebook_filename }
        return get_settings('spawner', 'pattern_dashboard_proxypath') % info

    @property
    def base_url(self):
        info = { 'containername': self.name }
        return get_settings('spawner', 'pattern_dashboard_baseurl') % info

    @property
    def volumemapping(self):
        return [
            (get_settings('spawner', 'volume-dashbaord-report'), '/mnt/.volumes/reports', 'ro'),
        ]

    @property
    def environment(self):
        return {
            'NB_USER': self.report.creator.username,
            'NB_URL': self.base_url,
            'NB_PORT': 8000,
            'NB_TOKEN': self.report.password,
            'REPORT_DIR': os.path.join('/mnt/.volumes/reports', self.report.report_dir),
            'REPORT_FILE': self.report.notebook_filename,
        }


class VolumeContainerBinding(models.Model):
    id = models.AutoField(primary_key = True)
    volume = models.ForeignKey(Volume, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
       return "%s-%s" % (self.container.name, self.volume.name)

