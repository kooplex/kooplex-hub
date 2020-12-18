import logging
import os
import datetime
import requests
import time

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.contrib.auth.models import User

from .project import Project, UserProjectBinding
from .report import Report
from .course import Course
from .volume import Volume, VolumeProjectBinding
from .image import Image

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str, now

from kooplex.lib import start_environment, stop_environment, check_environment

from .envvar import EnvVarMapping
from .proxy import Proxy

logger = logging.getLogger(__name__)



class Service(models.Model):
    ST_NOTPRESENT = 'np'
    ST_STARTING = 'starting'
    ST_RUNNING = 'run'
    ST_NEED_RESTART = 'restart'
    ST_ERROR = 'oops'
    ST_STOPPING = 'stopping'
    ST_LOOKUP = {
        ST_NOTPRESENT: 'Not present.',
        ST_STARTING: 'Starting...',
        ST_RUNNING: 'Running fine.',
        ST_NEED_RESTART: 'Restart required',
        ST_ERROR: 'Error occured.',
        ST_STOPPING: 'Stopping...',
    }

    name = models.CharField(max_length = 200, null = False)
    user = models.ForeignKey(User, null = False)
    suffix = models.CharField(max_length = 200, null = True, default = None)
    image = models.ForeignKey(Image, null = False)
    launched_at = models.DateTimeField(null = True)

    state = models.CharField(max_length = 16, choices = ST_LOOKUP.items(), default = ST_NOTPRESENT)
    restart_reasons = models.CharField(max_length = 512, null = True)
    last_message = models.CharField(max_length = 512, null = True)
    last_message_at = models.DateTimeField(default = None, null = True)

    class Meta:
        unique_together = [['user', 'name', 'suffix']]

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return f"<Service {self.name}@{self.user} -- {self.state}>"

    @property
    def label(self):
        return f"{self.user}-{self.name}-{self.suffix}" if self.suffix else f"{self.user}-{self.name}"

    @property
    def default_proxy(self):
        return Proxy.objects.get(image = self.image, default = True)

    @property
    def proxy_route(self):
        return self.default_proxy.proxy_route(self)

    @property
    def url_internal(self):
        return self.default_proxy.url_internal(self)

    @property
    def url_public(self):
        return self.default_proxy.url_public(self)

    def wait_until_ready(self):
        from kooplex.lib import keeptrying
        for _ in range(5):
            resp = keeptrying(method = requests.get, times = 5, url = self.url_public, timeout = .05)
            logger.info('Get %s -> [%d]' % (self.url_public, resp.status_code))
            time.sleep(.1)
            if resp.status_code != 503:
                return resp
            logger.warning('Proxy target missing: %s' % self.url_public)

    @property
    def env_variables(self):
        for envmap in EnvVarMapping.objects.filter(image = self.image):
            yield { "name": envmap.name, "value": envmap.valuemap.format(service = self) }

    @property
    def uptime(self):
        timenow = now()
        delta = timenow - self.launched_at
        return delta if self.is_running else -1

    @property
    def proxies(self):
        from .proxy import Proxy
        return list(Proxy.objects.filter(image = self.image))

    @property
    def projects(self):
        return [ binding.project for binding in ProjectServiceBinding.objects.filter(service = self) ]

    @property
    def synced_libraries(self):
        from .filesync import FSLibraryServiceBinding
        return [ binding.fslibrary for binding in FSLibraryServiceBinding.objects.filter(service = self) ]

    @property
    def repos(self):
        from .versioncontrol import VCProjectServiceBinding
        return [ binding.vcproject for binding in VCProjectServiceBinding.objects.filter(service = self) ]

    def start(self):
        return start_environment(self)

    def stop(self):
        self.restart_reasons = None
        self.save()
        return stop_environment(self)

    def check_state(self):
        return check_environment(self)

    def mark_restart(self, reason):
        if self.state not in [ self.ST_RUNNING, self.ST_NEED_RESTART ]:
            return False
        if self.restart_reasons:
            self.restart_reasons += ', ' + reason
        else:
            self.restart_reasons = reason
        self.state = self.ST_NEED_RESTART
        self.save()
        return True

@receiver(pre_delete, sender = Service)
def container_to_be_removed(sender, instance, **kwargs):
    try:
        stop_environment(instance)
        logger.info(f'- removed pod/container {instance.label}')
    except Exception as e:
        logger.warning(f'! check pod/container {instance.label}, during removal exception raised: -- {e}')


#@receiver(pre_save, sender = Container)
#def container_message_change(sender, instance, **kwargs):
#    is_new = instance.id is None
#    old_instance = Container() if is_new else Container.objects.get(id = instance.id)
#    if old_instance.last_message != instance.last_message:
#         logger.debug("msg of %s: %s" % (instance, instance.last_message))
#         instance.last_message_at = now()
#
#
#
#@receiver(post_save, sender = Container)
#def bind_home(sender, instance, created, **kwargs):
#    if created and instance.report is None:
#        try:
#            v_home = Volume.objects.get(volumetype = Volume.HOME)
#            VolumeContainerBinding.objects.create(container = instance, volume = v_home)
#        except Exception as e:
#            logger.error('Home not bound -- %s' % e)
#
#
#@receiver(post_save, sender = Container)
#def bind_report(sender, instance, created, **kwargs):
#    if created:# and not instance.course:
#        try:
#            v_report = Volume.objects.get(volumetype = Volume.REPORT)
#            VolumeContainerBinding.objects.create(container = instance, volume = v_report)
#        except Exception as e:
#            logger.error('Report not bound -- %s' % e)
#
#
#@receiver(post_save, sender = Container)
#def bind_garbage(sender, instance, created, **kwargs):
#    if created and instance.report is None:
#        try:
#            v_garbage = Volume.objects.get(volumetype = Volume.GARBAGE)
#            VolumeContainerBinding.objects.create(container = instance, volume = v_garbage)
#        except Exception as e:
#            logger.error('Garbage not bound -- %s' % e)
#
#@receiver(post_save, sender = Container)
#def bind_filesync(sender, instance, created, **kwargs):
#    if created and instance.report is None:
#        try:
#            v_filesync = Volume.objects.get(volumetype = Volume.FILESYNC)
#            VolumeContainerBinding.objects.create(container = instance, volume = v_filesync)
#        except Exception as e:
#            logger.error('Filesync not bound -- %s' % e)
#
class ProjectServiceBinding(models.Model):
    project = models.ForeignKey(Project, null = False)
    service = models.ForeignKey(Service, null = False)

    def __str__(self):
        return f"<ProjectServiceBinding {self.project}-{self.service}>"


#@receiver(post_save, sender = ProjectContainerBinding)
#def bind_share(sender, instance, created, **kwargs):
#    if created:
#        c = instance.container
#        try:
#            v_share = Volume.objects.get(volumetype = Volume.SHARE)
#            VolumeContainerBinding.objects.get(container = c, volume = v_share)
#            logger.debug('Share already bound to container %s' % c)
#        except VolumeContainerBinding.DoesNotExist:
#            VolumeContainerBinding.objects.create(container = c, volume = v_share)
#            logger.debug('Share bound to container %s' % c)
#        except Exception as e:
#            logger.error('Share not bound to container %s -- %s' % (c, e))
#
#@receiver(pre_delete, sender = ProjectContainerBinding)
#def container_to_be_removed(sender, instance, **kwargs):
#        logger.debug('Set %s container to be removed' % instance)
#        c = instance.container
#        c.marked_to_remove = True
#        c.save()
#
#
##@receiver(pre_delete, sender = ProjectContainerBinding)                                                   
#@receiver(pre_delete, sender = Container)    
#def container_environmentS(sender, instance, **kwargs):                                                   
#        c = instance                                                                             
#        remove_container_environment(c, 'PASSWORD')
#                                                                                                                                                                          
#
#@receiver(post_delete, sender = ProjectContainerBinding)
#def remove_bind_share(sender, instance, **kwargs):
#    c = instance.container
#    if not ProjectContainerBinding.objects.filter(container = c):
#        try:
#            v_share = Volume.objects.get(volumetype = Volume.SHARE)
#            VolumeContainerBinding.objects.get(container = c, volume = v_share).delete()
#            logger.debug('Share unbound from container %s' % instance)
#        except Exception as e:
#            logger.error('Share was not unbound from container %s -- %s' % (instance, e))
#
#
#
#@receiver(post_save, sender = ProjectContainerBinding)
#def bind_workdir(sender, instance, created, **kwargs):
#    if created:
#        c = instance.container
#        try:
#            v_workdir = Volume.objects.get(volumetype = Volume.WORKDIR)
#            VolumeContainerBinding.objects.get(container = c, volume = v_workdir)
#            logger.debug('Workdir already bound to container %s' % c)
#        except VolumeContainerBinding.DoesNotExist:
#            VolumeContainerBinding.objects.create(container = c, volume = v_workdir)
#            logger.debug('Workdir bound to container %s' % c)
#        except Exception as e:
#            logger.error('Workdir not bound to container %s -- %s' % (c, e))
#
#
#@receiver(post_delete, sender = ProjectContainerBinding)
#def remove_bind_workdir(sender, instance, **kwargs):
#    c = instance.container
#    if not ProjectContainerBinding.objects.filter(container = c):
#        try:
#            v_workdir = Volume.objects.get(volumetype = Volume.WORKDIR)
#            VolumeContainerBinding.objects.get(container = c, volume = v_workdir).delete()
#            logger.debug('Workdir unbound from container %s' % instance)
#        except Exception as e:
#            logger.error('Workdir was not unbound from container %s -- %s' % (instance, e))
#
#
#@receiver(post_save, sender = ProjectContainerBinding)
#def bind_git(sender, instance, created, **kwargs):
#    if created:
#        c = instance.container
#        try:
#            v_git = Volume.objects.get(volumetype = Volume.GIT)
#            VolumeContainerBinding.objects.get(container = c, volume = v_git)
#            logger.debug('Git cache already bound to container %s' % c)
#        except VolumeContainerBinding.DoesNotExist:
#            VolumeContainerBinding.objects.create(container = c, volume = v_git)
#            logger.debug('Git cache bound to container %s' % c)
#        except Exception as e:
#            logger.error('Git cache not bound to container %s -- %s' % (c, e))
#
#
#@receiver(post_delete, sender = ProjectContainerBinding)
#def remove_bind_git(sender, instance, **kwargs):
#    c = instance.container
#    if not ProjectContainerBinding.objects.filter(container = c):
#        try:
#            v_git = Volume.objects.get(volumetype = Volume.GIT)
#            VolumeContainerBinding.objects.get(container = c, volume = v_git).delete()
#            logger.debug('Git cache unbound from container %s' % instance)
#        except Exception as e:
#            logger.error('Git cache was not unbound from container %s -- %s' % (instance, e))
#
#
#@receiver(post_save, sender = ProjectContainerBinding)
#def bind_stg(sender, instance, created, **kwargs):
#    if created:
#        c = instance.container
#        for vpb in VolumeProjectBinding.objects.filter(project = instance.project, volume__volumetype = Volume.STORAGE):
#            v = vpb.volume
#            try:
#                VolumeContainerBinding.objects.get(container = c, volume = v)
#                logger.debug('Storage bound to container %s' % c)
#            except VolumeContainerBinding.DoesNotExist:
#                VolumeContainerBinding.objects.create(container = c, volume = v)
#                logger.debug('Storage bound to container %s' % c)
#            except Exception as e:
#                logger.error('Storage not bound to container %s -- %s' % (c, e))
#
#@receiver(post_save, sender = ProjectContainerBinding)
#def bind_vol(sender, instance, created, **kwargs):
#    if created:
#        c = instance.container
#        for vpb in VolumeProjectBinding.objects.filter(project = instance.project, volume__volumetype = Volume.FUNCTIONAL):
#            v = vpb.volume
#            try:
#                VolumeContainerBinding.objects.get(container = c, volume = v)
#                logger.debug('Functional volume bound to container %s' % c)
#            except VolumeContainerBinding.DoesNotExist:
#                VolumeContainerBinding.objects.create(container = c, volume = v)
#                logger.debug('Functional volume was not bound, binding now to container %s' % c)
#            except Exception as e:
#                logger.error('Functional volume not bound to container %s -- %s' % (c, e))
#
#
##FIXME: remove_bind_stg
#
#
#@receiver(post_save, sender = ProjectContainerBinding)
#def managemount_add_project(sender, instance, created, **kwargs):
#    if created:
#        c = instance.container
#        try:
#            c.managemount()
#        except Exception as e:
#            logger.error('Container %s -- %s' % (c, e))
#
#
#@receiver(post_delete, sender = ProjectContainerBinding)
#def managemount_remove_project(sender, instance, **kwargs):
#    c = instance.container
#    try:
#        c.managemount()
#    except Exception as e:
#        logger.error('Container %s -- %s' % (c, e))
#
#
#@receiver(post_save, sender = VCProjectProjectBinding)
#def managemount_add_vcprojectprojectbinding(sender, instance, created, **kwargs):
#    if created:
#        for c in Container.objects.filter(user = instance.vcproject.token.user, state = Container.ST_RUNNING):
#            try:
#                c.managemount()
#            except Exception as e:
#                logger.error('Container %s -- %s' % (c, e))
#
#
#@receiver(post_delete, sender = VCProjectProjectBinding)
#def managemount_remove_vcprojectprojectbinding(sender, instance, **kwargs):
#    for c in Container.objects.filter(user = instance.vcproject.token.user, state = Container.ST_RUNNING):
#        try:
#            c.managemount()
#        except Exception as e:
#            logger.error('Container %s -- %s' % (c, e))
#
#
#@receiver(post_delete, sender = ProjectContainerBinding)
#def assert_container_has_projects(sender, instance, **kwargs):
#    container = instance.container
#    if container.n_projects == 0:
#        container.state = Container.ST_NOTPRESENT
#        container.save()
#         
#
#
#
#class VolumeContainerBinding(models.Model):
#    volume = models.ForeignKey(Volume, null = False)
#    container = models.ForeignKey(Container, null = False)
#
#    def __str__(self):
#       return "%s-%s" % (self.container.name, self.volume.name)
#
#    @staticmethod
#    def list_containervolumes(container):
#        for binding in VolumeContainerBinding.objects.filter(container = container):
#            yield binding.volume
#               
#
#@receiver(pre_save, sender = ProjectContainerBinding)
#def update_image(sender, instance, **kwargs):
#    if instance.container.image is None:
#        instance.container.image = instance.project.image
#        instance.container.save()
#        logger.debug("container (%s) image is set %s" % (instance.container, instance.container.image))
#    if instance.project.image is not None:
#        assert instance.container.image == instance.project.image, "Conflicting images %s =/= %s" % (instance.container.image, instance.project.image)
#
#
#
#@receiver(pre_save, sender = Project)
#def container_check_image(sender, instance, **kwargs):
#    try:
#        old = sender.objects.get(id = instance.id)
#    except sender.DoesNotExist:
#        return
#    if old.image != instance.image:
#        pcbs = ProjectContainerBinding.objects.filter(project = instance)
#        for pcb in pcbs:
#            c = pcb.container
#            #assert c.image is None or c.image == instance.image, "Conflict with container %s" % c #FIXME: ez igy nem jo
#        for pcb in pcbs:
#            c = pcb.container
#            if c.is_running or c.is_stopped:
#                c.marked_to_remove = True
#            c.image = instance.image
#            c.save()
#
#
#
#
#class CourseContainerBinding(models.Model):
#    course = models.ForeignKey(Course, null = False)
#    container = models.ForeignKey(Container, null = False)
#
#    def __str__(self):
#        return "<CourseContainerBinding %s-%s>" % (self.course, self.container)
#
#
#@receiver(pre_save, sender = Course)
#def update_courseimage(sender, instance, **kwargs):
#    ccbs = CourseContainerBinding.objects.filter(course = instance)
#    for ccb in ccbs:
#        c = ccb.container
#        if c.is_running or c.is_stopped:
#            c.marked_to_remove = True
#        c.image = instance.image
#        c.save()
#        logger.debug("container (%s) image is set %s" % (c, c.image))
#
#
#@receiver(pre_save, sender = CourseContainerBinding)
#def update_course_image(sender, instance, **kwargs):
#    if instance.container.image is None:
#        instance.container.image = instance.course.image
#        instance.container.save()
#        logger.debug("container (%s) image is set %s" % (instance.container, instance.container.image))
#    if instance.course.image is not None:
#        assert instance.container.image == instance.course.image, "Conflicting images %s =/= %s" % (instance.container.image, instance.course.image)
#
#
#@receiver(post_save, sender = CourseContainerBinding)
#def bind_courserelatedvolumes(sender, instance, created, **kwargs):
#    if created:
#        for vt in [ Volume.COURSE_SHARE, Volume.COURSE_WORKDIR, Volume.COURSE_ASSIGNMENTDIR ]:
#            try:
#                volume = Volume.objects.get(volumetype = vt)
#                binding = VolumeContainerBinding.objects.create(container = instance.container, volume = volume)
#                logger.debug("binding created %s" % binding)
#            except Volume.DoesNotExist:
#                logger.error("cannot create binding coursecontainerbinding %s volume %s" % (instance, vt))
#
#
#class ReportContainerBinding(models.Model):
#    report = models.ForeignKey(Report, null = False)
#    container = models.ForeignKey(Container, null = False)
#
#    def __str__(self):
#        return "<ReportContainerBinding %s-%s>" % (self.report, self.container)
#
#@receiver(post_save, sender = ReportContainerBinding)
#def bind_reportvolume(sender, instance, created, **kwargs):
#    if created:
#        try:
#            volume = Volume.objects.get(volumetype = Volume.REPORT)
#            binding = VolumeContainerBinding.objects.create(container = instance.container, volume = volume)
#            logger.debug("binding created %s" % binding)
#        except Volume.DoesNotExist:
#            logger.error("cannot create binding coursecontainerbinding %s volume %s" % (instance, vt))

