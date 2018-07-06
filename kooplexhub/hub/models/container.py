import logging
import os
import datetime
import requests
import time

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.contrib.auth.models import User

from .course import Course, UserCourseBinding
from .project import Project
from .volume import Volume, VolumeProjectBinding
from .image import Image

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str

logger = logging.getLogger(__name__)


#FIXME: container state machinery rewrite
#FIXME: when docker container is created, manage mount_report.conf

class Container(models.Model):
    name = models.CharField(max_length = 200, null = False)
    user = models.ForeignKey(User, null = False)
    image = models.ForeignKey(Image, null = True)
    launched_at = models.DateTimeField(default = timezone.now)
    is_running = models.BooleanField(default = False)
    marked_to_remove = models.BooleanField(default = False)

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return "<Container %s@%s>" % (self.name, self.user)

    @property
    def uptime(self):
        now = datetime.datetime.now(tz = datetime.timezone.utc)
        delta = now - self.launched_at
        return delta if self.is_running else -1

    @property
    def url(self):
        return "http://%s:%d" % (self.name, KOOPLEX.get('spawner', {}).get('port', 8000))

    @property
    def url_external(self):
        return os.path.join(KOOPLEX['base_url'], self.proxy_path, '?token=%s' % self.user.profile.token)

    @property
    def proxy_path(self):
        info = { 'containername': self.name }
        return KOOPLEX['spawner']['pattern_proxypath'] % info

    @property
    def projects(self):
        for binding in ProjectContainerBinding.objects.filter(container = self):
            yield binding.project

    @property
    def volumecontainerbindings(self):
        for binding in VolumeContainerBinding.objects.filter(container = self):
            yield binding

    @property
    def volumes(self):
        for volume in VolumeContainerBinding.list_containervolumes(container = self):
            yield volume

    def wait_until_ready(self):
        from kooplex.lib import keeptrying
        return keeptrying(method = requests.get, times = 10, url =self.api)

    @property
    def n_projects(self):
        return len(list(self.projects))

    def is_user_authorized(self, user):
        for project in self.projects:
            if project.is_user_authorized(user):
                return True
        return False

    @staticmethod
    def get_userprojectcontainer(user, project_id, create):
        logger.debug("project id %s & user %s" % (project_id, user))
        project = Project.get_userproject(project_id, user)
        logger.debug("found project %s and authorized for user %s" % (project, user))
        for binding in ProjectContainerBinding.objects.filter(project = project):
            if binding.container.user == user:
                logger.debug("container in db %s" % binding.container)
                return binding.container
        if create:
            containername = "%s-%s" % (project.name, user.username)
            container = Container.objects.create(name = containername, user = user)
            ProjectContainerBinding.objects.create(project = project, container = container)
            logger.debug("new container in db %s" % container)
            return container 
        raise Container.DoesNotExist

    @staticmethod
    def get_usercontainer(user, container_id, **kw):
        logger.debug("container id %s & user %s" % (container_id, user))
        container = Container.objects.get(id = container_id, **kw)
        if not container.is_user_authorized(user):
            raise Container.DoesNotExists("Unauthorized request")
        logger.debug("found container %s and authorized for user %s" % (container, user))
        return container 

    def docker_start(self):
        from kooplex.lib import Docker
        from kooplex.lib.proxy import addroute
        if self.is_running:
            logger.error("%s is running" % self)
            return
        docker = Docker()
        docker.run_container(self)
        self.is_running = True
        self.save()
        addroute(self)
        logger.info("started %s" % self)

    def docker_stop(self, remove = False):
        from kooplex.lib import Docker
        from kooplex.lib.proxy import removeroute
        try:
            removeroute(self)
        except KeyError:
            logger.warning("The proxy path was not existing: %s" % self)
            pass
        Docker().stop_container(self)
        if remove or self.marked_to_remove:
            Docker().remove_container(self)

    @property
    def environment(self):
        envs = {
            'NB_USER': self.user.username,
            'NB_UID': self.user.profile.userid,
            'NB_GID': self.user.profile.groupid,
            'NB_URL': self.proxy_path,
            'NB_PORT': KOOPLEX.get('spawner', {}).get('port', 8000),
            'NB_TOKEN': self.user.profile.token,
            'CONTAINER_NAME': self.name,
        }
        return envs

    @property
    def api(self):
        return os.path.join(self.url, 'notebook', self.proxy_path)

    @staticmethod
    def manage_report_mount(user, project, mapping):
        from kooplex.lib import Docker 
        try: 
            container = Container.get_userprojectcontainer(user = user, project_id = project.id, create = False) 
            if container.is_running:
                logger.debug("container %s found and is running" % container) 
                Docker().reportmount(container, mapping)
            else:
                logger.debug("container %s is not running" % container) 
        except Exception as e: 
            logger.error("cannot manage mapping this time -- %s" % e) 


class ProjectContainerBinding(models.Model):
    project = models.ForeignKey(Project, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
        return "<ProjectContainerBinding %s-%s>" % (self.project, self.container)

  
#class ProjectContainer(ContainerBase):
#    project = models.ForeignKey(Project, null = True)
#    mark_to_remove = models.BooleanField(default = False)
#    volume_gids = set()
#
#    def __str__(self):
#        return "<ProjectContainer: %s of %s@%s>" % (self.name, self.user, self.project)
#
#    def init(self):
#        container_name_info = { 'username': self.user.username, 'projectname': self.project.name_with_owner }
#        self.name = get_settings('spawner', 'pattern_project_containername') % container_name_info
#        self.image = self.project.image
#        for vpb in VolumeProjectBinding.objects.filter(project = self.project):
#            vcb = VolumeContainerBinding(container = self, volume = vpb.volume)
#            vcb.save()
#            logger.debug('container volume binding %s' % vcb)
#            try:
#                vol = StorageVolume.objects.get(id = vpb.volume.id)
#                if vol.groupid is None:
#                    logger.warning("storage volume %s does not have a group id associated" % vol)
#                    continue
#                self.volume_gids.add(vol.groupid)
#                logger.debug("storage volume %s associated group id %d" % (vol, vol.groupid))
#            except StorageVolume.DoesNotExist:
#                # a functional volume does not have a groupid
#                pass
#
#    @property
#    def url_external(self):
#        return os.path.join(get_settings('hub', 'base_url'), self.proxy_path, '?token=%s' % self.user.token)
#
#    @property
#    def api(self):
#        return os.path.join(self.url, 'notebook', self.proxy_path)
#
#    @property
#    def volumemapping(self):
#        return [
#            (get_settings('spawner', 'volume-home'), '/mnt/.volumes/home', 'rw'),
#            (get_settings('spawner', 'volume-git'), '/mnt/.volumes/git', 'rw'),
#            (get_settings('spawner', 'volume-share'), '/mnt/.volumes/share', 'rw'),
#        ]
#
#    @property
#    def environment(self):
#        envs = {
#            'NB_USER': self.user.username,
#            'NB_UID': self.user.uid,
#            'NB_GID': self.user.gid,
#            'NB_URL': self.proxy_path,
#            'NB_PORT': 8000,
#            'NB_TOKEN': self.user.token,
#            'PR_ID': self.project.id,
#            'PR_NAME': self.project.name,
#            'PR_PWN': self.project.name_with_owner,
#        }
#        if len(self.volume_gids):
#            envs['MNT_GIDS'] = ",".join([ str(x) for x in self.volume_gids ])
#        return envs

#class CourseContainer(ContainerBase):
##    project = models.ForeignKey(CourseProject, null = True)
#
#    def __str__(self):
#        return "<CourseContainer: %s of %s@%s>" % (self.name, self.user, self.project)
#
#    @property
#    def mark_to_remove(self): return True
#    @mark_to_remove.setter
#    def mark_to_remove(self, m): pass
#    
#
#    def init(self):
#        container_name_info = { 'username': self.user.username, 'projectname': self.project.name }
#        self.name = KOOPLEX.get('spawner', {}).get('pattern_courseproject_containername', 'course-%(projectname)s-%(username)s') % container_name_info
#        self.image = self.project.image
###        for vpb in VolumeProjectBinding.objects.filter(project = self.project):
###            vcb = VolumeContainerBinding.objects.create(container = self, volume = vpb.volume)
###            logger.debug('container volume binding %s' % vcb)
###            try:
###                vol = StorageVolume.objects.get(id = vpb.volume.id)
###                if vol.groupid is None:
###                    logger.warning("storage volume %s does not have a group id associated" % vol)
###                    continue
###                self.volume_gids.add(vol.groupid)
###                logger.debug("storage volume %s associated group id %d" % (vol, vol.groupid))
###            except StorageVolume.DoesNotExist:
###                # a functional volume does not have a groupid
###                pass
#

class VolumeContainerBinding(models.Model):
    volume = models.ForeignKey(Volume, null = False)
    container = models.ForeignKey(Container, null = False)
    project = models.ForeignKey(Project, null = False)

    def __str__(self):
       return "%s-%s" % (self.container.name, self.volume.name)

    @staticmethod
    def list_containervolumes(container):
        for binding in VolumeContainerBinding.objects.filter(container = container):
            yield binding.volume
               

@receiver(pre_save, sender = ProjectContainerBinding)
def update_image(sender, instance, **kwargs):
    if instance.container.image is None:
        instance.container.image = instance.project.image
        instance.container.save()
        logger.debug("container (%s) image is set %s" % (instance.container, instance.container.image))
    if instance.project.image is not None:
        assert instance.container.image == instance.project.image, "Conflicting images %s =/= %s" % (instance.container.image, instance.project.image)

@receiver(pre_save, sender = ProjectContainerBinding)
def update_volumecontainerbinding(sender, instance, **kwargs):
    def process(project):
        for volume in project.volumes:
            try:
                binding = VolumeContainerBinding.objects.get(volume = volume, container = container, project = instance.project)
                try:
                    bindings.remove(binding)
                except ValueError:
                    pass
                logger.debug("binding not modified: %s" % binding)
            except VolumeContainerBinding.DoesNotExist:
                binding = VolumeContainerBinding.objects.create(volume = volume, container = container, project = instance.project)
                logger.debug("binding created: %s" % binding)
    container = instance.container
    bindings = list(VolumeContainerBinding.objects.filter(container = container))
    process(instance.project)
    for project in container.projects:
        process(project)
    for binding in bindings:
        logger.debug("binding removed: %s" % binding)
        binding.delete()

