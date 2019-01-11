import logging
import os
import datetime
import requests
import time

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.contrib.auth.models import User

from .project import Project
from .volume import Volume, VolumeProjectBinding
from .image import Image

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str, now

logger = logging.getLogger(__name__)


ST_LOOKUP = {
    'np': 'Not present in docker engine.',
    'man': 'Manifested but not running.',
    'run': 'Running in docker engine.',
}

class Container(models.Model):
    ST_NOTPRESENT = 'np'
    ST_NOTRUNNING = 'man'
    ST_RUNNING = 'run'
    STATE_LIST = [ ST_NOTPRESENT, ST_NOTRUNNING, ST_RUNNING ]

    name = models.CharField(max_length = 200, null = False)
    user = models.ForeignKey(User, null = False)
    image = models.ForeignKey(Image, null = True)
    launched_at = models.DateTimeField(default = timezone.now)
    marked_to_remove = models.BooleanField(default = False)

    state = models.CharField(max_length = 16, choices = [ (x, ST_LOOKUP[x]) for x in STATE_LIST ], default = ST_NOTPRESENT)
    last_message = models.CharField(max_length = 512, null = True)
    last_message_at = models.DateTimeField(default = None, null = True)


    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return "<Container %s@%s>" % (self.name, self.user)

    @property
    def is_created(self):
        return self.state != self.ST_NOTPRESENT

    @property
    def is_running(self):
        return self.state == self.ST_RUNNING

    @property
    def is_stopped(self):
        return self.state == self.ST_NOTRUNNING

    @property
    def uptime(self):
        timenow = now()
        delta = timenow - self.launched_at
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
    def userprojectbindings(self):
        from .project import UserProjectBinding
        for project in self.projects:
            yield UserProjectBinding.objects.get(user = self.user, project = project)

    @property
    def vcprojectprojectbindings(self):
        from .versioncontrol import VCProjectProjectBinding
        for project in self.projects:
            for vcppb in VCProjectProjectBinding.objects.filter(project = project):
                if vcppb.vcproject.token.user == self.user:
                    yield vcppb

    @property
    def projects_addable(self):
        from .project import UserProjectBinding
        bound_projects = set(self.projects)
        for binding in UserProjectBinding.objects.filter(user = self.user):
            if binding.project in bound_projects:
                continue
            img = binding.project.image
            if self.image is None or img is None or self.image == img:
                yield binding.project

    @property
    def volumecontainerbindings(self):
        for binding in VolumeContainerBinding.objects.filter(container = self):
            logger.debug(binding)
            yield binding

    @property
    def volumes(self):
        for volume in VolumeContainerBinding.list_containervolumes(container = self):
            logger.debug(volume)
            yield volume

    def wait_until_ready(self):
        from kooplex.lib import keeptrying
        return keeptrying(method = requests.get, times = 10, url = self.api)

    @property
    def n_projects(self):
        return len(list(self.projects))

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

    def docker_start(self):
        self.state = self.ST_RUNNING
        self.save()

    def docker_stop(self):
        self.state = self.ST_NOTRUNNING
        self.save()

    def docker_remove(self):
        self.state = self.ST_NOTPRESENT
        self.save()

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

    def managemount(self):
        from kooplex.lib import Docker
        try: 
            assert self.is_created, "%s is not manifested in docker engine"
            Docker().managemount(self)
        except Exception as e: 
            logger.error("cannot manage mapping in container %s -- %s" % (self, e)) 

    def refresh_state(self):
        from kooplex.lib import Docker 
        try:
            Docker().refresh_container_state(self)
        except TypeError:
            pass


@receiver(pre_save, sender = Container)
def container_attribute_change(sender, instance, **kwargs):
#FIXME: atomokra bontani
    from kooplex.lib import Docker
    from kooplex.lib.proxy import addroute, removeroute
    is_new = sender.id is not None
    old_instance = sender() if is_new else sender.objects.get(id = instance.id)
    docker = Docker()
    if not is_new and old_instance.image != instance.image:
         if instance.state == sender.ST_RUNNING:
             instance.marked_to_remove = True
         elif instance.state != sender.ST_NOTPRESENT:
             docker.remove_container(instance)
             instance.marked_to_remove = False
             instance.state = sender.ST_NOTPRESENT
    if old_instance.state != instance.state:
        logger.debug("%s statchange %s -> %s" % (instance, ST_LOOKUP[old_instance.state], ST_LOOKUP[instance.state]))
        if not old_instance.is_running and instance.is_running:
            docker.run_container(instance)
            addroute(instance)
            logger.info("started %s" % instance)
        elif not instance.is_running:
            try:
                removeroute(instance)
            except KeyError:
                logger.warning("The proxy path was not existing: %s" % instance)
            docker.stop_container(instance)
            if instance.state == sender.ST_NOTPRESENT or instance.marked_to_remove:
                docker.remove_container(instance)
                instance.marked_to_remove = False
                instance.state = sender.ST_NOTPRESENT
        else:
            raise NotImplementedError
    if old_instance.last_message != instance.last_message:
         logger.debug("msg of %s: %s" % (instance, instance.last_message))
         instance.last_message_at = now()

@receiver(post_save, sender = Container)
def bind_home(sender, instance, created, **kwargs):
    if created:
        try:
            v_home = Volume.objects.get(volumetype = Volume.HOME['tag'])
            VolumeContainerBinding.objects.create(container = instance, volume = v_home)
        except Exception as e:
            logger.error('Home not bound -- %s' % e)



class ProjectContainerBinding(models.Model):
    project = models.ForeignKey(Project, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
        return "<ProjectContainerBinding %s-%s>" % (self.project, self.container)


@receiver(post_save, sender = ProjectContainerBinding)
def bind_share(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        try:
            v_share = Volume.objects.get(volumetype = Volume.SHARE['tag'])
            VolumeContainerBinding.objects.get(container = c, volume = v_share)
            logger.debug('Share already bound to container %s' % c)
        except VolumeContainerBinding.DoesNotExist:
            VolumeContainerBinding.objects.create(container = c, volume = v_share)
            logger.debug('Share bound to container %s' % c)
        except Exception as e:
            logger.error('Share not bound to container %s -- %s' % (c, e))
  
@receiver(post_delete, sender = ProjectContainerBinding)
def remove_bind_share(sender, instance, **kwargs):
    c = instance.container
    if not ProjectContainerBinding.objects.filter(container = c):
        try:
            v_share = Volume.objects.get(volumetype = Volume.SHARE['tag'])
            VolumeContainerBinding.objects.get(container = c, volume = v_share).delete()
            logger.debug('Share unbound from container %s' % instance)
        except Exception as e:
            logger.error('Share was not unbound from container %s -- %s' % (instance, e))



@receiver(post_save, sender = ProjectContainerBinding)
def bind_workdir(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        try:
            v_workdir = Volume.objects.get(volumetype = Volume.WORKDIR['tag'])
            VolumeContainerBinding.objects.get(container = c, volume = v_workdir)
            logger.debug('Workdir already bound to container %s' % c)
        except VolumeContainerBinding.DoesNotExist:
            VolumeContainerBinding.objects.create(container = c, volume = v_workdir)
            logger.debug('Workdir bound to container %s' % c)
        except Exception as e:
            logger.error('Workdir not bound to container %s -- %s' % (c, e))
  
@receiver(post_delete, sender = ProjectContainerBinding)
def remove_bind_workdir(sender, instance, **kwargs):
    c = instance.container
    if not ProjectContainerBinding.objects.filter(container = c):
        try:
            v_workdir = Volume.objects.get(volumetype = Volume.WORKDIR['tag'])
            VolumeContainerBinding.objects.get(container = c, volume = v_workdir).delete()
            logger.debug('Workdir unbound from container %s' % instance)
        except Exception as e:
            logger.error('Workdir was not unbound from container %s -- %s' % (instance, e))


@receiver(post_save, sender = ProjectContainerBinding)
def bind_git(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        try:
            v_git = Volume.objects.get(volumetype = Volume.GIT['tag'])
            VolumeContainerBinding.objects.get(container = c, volume = v_git)
            logger.debug('Git cache already bound to container %s' % c)
        except VolumeContainerBinding.DoesNotExist:
            VolumeContainerBinding.objects.create(container = c, volume = v_git)
            logger.debug('Git cache bound to container %s' % c)
        except Exception as e:
            logger.error('Git cache not bound to container %s -- %s' % (c, e))
  
@receiver(post_delete, sender = ProjectContainerBinding)
def remove_bind_git(sender, instance, **kwargs):
    c = instance.container
    if not ProjectContainerBinding.objects.filter(container = c):
        try:
            v_git = Volume.objects.get(volumetype = Volume.GIT['tag'])
            VolumeContainerBinding.objects.get(container = c, volume = v_git).delete()
            logger.debug('Git cache unbound from container %s' % instance)
        except Exception as e:
            logger.error('Git cache was not unbound from container %s -- %s' % (instance, e))

#FIXME: if volumes are added and removed the same time mounter runs twice in user container. It is an overhead better combine them some time together!
@receiver(post_save, sender = ProjectContainerBinding)
def managemount_add(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        try:
            c.managemount()
        except Exception as e:
            logger.error('Share not bound to container %s -- %s' % (c, e))

@receiver(post_delete, sender = ProjectContainerBinding)
def managemount_remove(sender, instance, **kwargs):
    c = instance.container
    try:
        c.managemount()
    except Exception as e:
        logger.error('Share not bound to container %s -- %s' % (c, e))
#######################################################################################################################################################

#@receiver(pre_save, sender = ProjectContainerBinding)
#def update_volumecontainerbinding(sender, instance, **kwargs):
#    def process(project):
#        for volume in project.volumes:
#            try:
#                binding = VolumeContainerBinding.objects.get(volume = volume, container = container, project = instance.project)
#                try:
#                    bindings.remove(binding)
#                except ValueError:
#                    pass
#                logger.debug("binding not modified: %s" % binding)
#            except VolumeContainerBinding.DoesNotExist:
#                binding = VolumeContainerBinding.objects.create(volume = volume, container = container, project = instance.project)
#                logger.debug("binding created: %s" % binding)
#    container = instance.container
#    bindings = list(VolumeContainerBinding.objects.filter(container = container))
#    process(instance.project)
#    for project in container.projects:
#        process(project)
#    for binding in bindings:
#        logger.debug("binding removed: %s" % binding)
#        binding.delete()

class VolumeContainerBinding(models.Model):
    volume = models.ForeignKey(Volume, null = False)
    container = models.ForeignKey(Container, null = False)
    #project = models.ForeignKey(Project, null = False)

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







@receiver(pre_save, sender = Project)
def container_check_image(sender, instance, **kwargs):
    try:
        old = sender.objects.get(id = instance.id)
    except sender.DoesNotExist:
        return
    if old.image != instance.image:
        pcbs = ProjectContainerBinding.objects.filter(project = instance)
        for pcb in pcbs:
            c = pcb.container
            #assert c.image is None or c.image == instance.image, "Conflict with container %s" % c #FIXME: ez igy nem jo
        for pcb in pcbs:
            c = pcb.container
            if c.is_running or c.is_stopped:
                c.marked_to_remove = True
            c.image = instance.image
            c.save()
