import logging
import re
import os
from django.db import models
from django.utils import timezone
import datetime
import requests
import time

from kooplex.lib import get_settings, standardize_str

from .user import User
from .project import Project
from .volume import Volume, VolumeProjectBinding, StorageVolume
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
    def uptime(self):
        now = datetime.datetime.now(tz = datetime.timezone.utc)
        delta = now - self.launched_at
        return delta if self.is_running else -1

    @property
    def url(self):
        return "http://%s:%d" % (self.name, 8000) #FIXME: PORT hardcoded

    @property
    def proxy_path(self):
        info = { 'containername': self.name }
        return get_settings('spawner', 'pattern_proxypath') % info

    @property
    def volumes(self):
        from .volume import lookup
        for vcb in VolumeContainerBinding.objects.filter(container = self):
            yield lookup( vcb.volume )

    def wait_until_ready(self):
        url = self.api
        while (True):
            try:
                logger.debug('Try to connect to notebook server in container %s' % self)
                response = requests.get(url)
                logger.debug('Connect to notebook server in container %s -- %s' % (self, response))
                break
            except Exception as e:
                logger.debug('Cannot connect to notebook server in container %s, sleeping...' % self)
                time.sleep(.1)

class ProjectContainer(Container):
    project = models.ForeignKey(Project, null = True)
    mark_to_remove = models.BooleanField(default = False)
    volume_gids = set()

    def __str__(self):
        return "<ProjectContainer: %s of %s@%s>" % (self.name, self.user, self.project)

    def init(self):
        container_name_info = { 'username': self.user.username, 'projectname': self.project.name_with_owner }
        self.name = get_settings('spawner', 'pattern_project_containername') % container_name_info
        self.image = self.project.image
        for vpb in VolumeProjectBinding.objects.filter(project = self.project):
            vcb = VolumeContainerBinding(container = self, volume = vpb.volume)
            vcb.save()
            logger.debug('container volume binding %s' % vcb)
            try:
                vol = StorageVolume.objects.get(id = vpb.volume.id)
                if vol.groupid is None:
                    logger.warning("storage volume %s does not have a group id associated" % vol)
                    continue
                self.volume_gids.add(vol.groupid)
                logger.debug("storage volume %s associated group id %d" % (vol, vol.groupid))
            except StorageVolume.DoesNotExist:
                # a functional volume does not have a groupid
                pass

    @property
    def url_external(self):
        return os.path.join(get_settings('hub', 'base_url'), self.proxy_path, '?token=%s' % self.user.token)

    @property
    def api(self):
        return os.path.join(self.url, 'notebook', self.proxy_path)

    @property
    def volumemapping(self):
        return [
            (get_settings('spawner', 'volume-home'), '/mnt/.volumes/home', 'rw'),
            (get_settings('spawner', 'volume-git'), '/mnt/.volumes/git', 'rw'),
            (get_settings('spawner', 'volume-share'), '/mnt/.volumes/share', 'rw'),
        ]

    @property
    def environment(self):
        envs = {
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
        if len(self.volume_gids):
            envs['MNT_GIDS'] = ",".join([ str(x) for x in self.volume_gids ])
        return envs

class LimitReached(Exception):
    pass

def filter_dashboardcontainers(report):
    from .report import DashboardReport
    for r in DashboardReport.objects.filter(creator = report.creator, name = report.name, project = report.project):
        for dbc in DashboardContainer.objects.filter(report = r):
            if dbc.name == None:
                logger.warning("check database for dashboard containers without a name %s" % (dbc))
                continue
            yield dbc

class DashboardContainer(Container):
    from .report import DashboardReport
    report = models.ForeignKey(DashboardReport, null = True)

    def __str__(self):
        return "<DashboardContainer: %s of %s@%s>" % (self.name, self.user, self.report)

    def init(self):
        dashboardlimit = get_settings('spawner', 'max_dashboards_per_report')
        dashboardnamefilter = get_settings('spawner', 'pattern_dashboard_containername_filter')
        pool = list(range(dashboardlimit))
        for dbc in filter_dashboardcontainers(self.report):
            _, _, used_id, _ = re.split(dashboardnamefilter, dbc.name)
            used_id = int(used_id)
            pool.remove(used_id)
            logger.debug("dashboard id %d for report %s is occupied" % (used_id, self.report))
        logger.debug("LEFT %d" % len(pool))
        if len(pool) == 0:
            logger.warning("%s dashboard report reached the limits of %d containers" % (self.report, dashboardlimit))
            self.delete()
            raise LimitReached("Cannot launch any more dashboard containers for report %s" % self.report.name)
        container_name_info = { 'instance_id': pool.pop(), 'reportname': standardize_str(self.report.name) }
        self.name = get_settings('spawner', 'pattern_dashboard_containername') % container_name_info
        self.image = self.report.project.image
        for vpb in VolumeProjectBinding.objects.filter(project = self.report.project):
            vcb = VolumeContainerBinding(container = self, volume = vpb.volume)
            vcb.save()
        self.save() #FIXME: breaks symmetry

    @property
    def volumemapping(self):
        return [
            (get_settings('spawner', 'volume-dashboard-report'), '/mnt/.volumes/reports', 'ro'),
        ]

    @property
    def environment(self):
        return {
            'NB_USER': self.report.creator.username,
            'NB_URL': self.proxy_path,
            'NB_PORT': 8000,
            'NB_TOKEN': self.report.password,
            'REPORT_DIRANDFILE': self.report.nb_path,
            'REPORT_DIR': os.path.join('/mnt/.volumes/reports', self.report.report_dir),
            'REPORT_FILE': self.report.notebook_filename,
        }

    @property
    def url_external(self):
        return os.path.join(get_settings('hub', 'base_url'), self.proxy_path, 'notebooks', '%s?dashboard' % self.report.nb_path)

    @property
    def mark_to_remove(self):
        return True

    @property
    def api(self):
        return os.path.join(self.url, self.proxy_path)



class VolumeContainerBinding(models.Model):
    id = models.AutoField(primary_key = True)
    volume = models.ForeignKey(Volume, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
       return "%s-%s" % (self.container.name, self.volume.name)

