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

from kooplex.lib import start_environment, stop_environment, restart_environment, check_environment

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
    suffix = models.CharField(max_length = 200, null = True, default = None, blank = True)
    image = models.ForeignKey(Image, null = False)
    launched_at = models.DateTimeField(null = True, blank = True)

    state = models.CharField(max_length = 16, choices = ST_LOOKUP.items(), default = ST_NOTPRESENT)
    restart_reasons = models.CharField(max_length = 512, null = True)
    last_message = models.CharField(max_length = 512, null = True)
    last_message_at = models.DateTimeField(default = None, null = True, blank = True)

    class Meta:
        unique_together = [['user', 'name', 'suffix']]

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return f"<Service {self.name}@{self.user} -- {self.state}>"

    @property
    def label(self):
        n = standardize_str(self.name)
        return f"{self.user}-{n}-{self.suffix}".lower() if self.suffix else f"{self.user}-{n}".lower()

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
    def reports(self):
        "relevant only for project containers"
        ##This is elegant but is buggy in current django version! update() also sucks
        ##reports = Report.objects.none()
        ##for p in self.projects:
        ##    reports = reports.union( Report.objects.filter(project = p) )
        ##return reports
        reports = Report.objects.none()
        for p in self.projects:
            if len( reports ) == 0:
                reports = Report.objects.filter(project = p)
            else:
                reports = reports.union( Report.objects.filter(project = p) )
        return reports

    @property
    def report(self):
        "relevant only for report containers"
        return ReportServiceBinding.objects.get(service = self).report

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

    def restart(self):
        self.restart_reasons = None
        self.save()
        return restart_environment(self)

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
def remove_container(sender, instance, **kwargs):
    try:
        stop_environment(instance)
        logger.info(f'- removed pod/container {instance.label}')
    except Exception as e:
        logger.warning(f'! check pod/container {instance.label}, during removal exception raised: -- {e}')



class ProjectServiceBinding(models.Model):
    project = models.ForeignKey(Project, null = False)
    service = models.ForeignKey(Service, null = False)

    def __str__(self):
        return f"<ProjectServiceBinding {self.project}-{self.service}>"



class ReportServiceBinding(models.Model):
    report = models.ForeignKey(Report, null = False)
    service = models.ForeignKey(Service, null = False)

    def __str__(self):
        return f"<ReportServiceBinding {self.report}-{self.service}>"

@receiver(post_save, sender = Report)
def create_report_service(sender, instance, created, **kwargs):
    if created:
        svc = Service.objects.create(name = instance.cleanname, user = instance.creator, suffix = 'report', image = instance.image)
        logger.info(f'+ created service {svc.name} for report {instance.name}')
        ReportServiceBinding.objects.create(report = instance, service = svc)
        svc.start()
        logger.info(f'started report service {svc.label}')

@receiver(post_delete, sender = ReportServiceBinding)
def remove_report_service(sender, instance, **kwargs):
    svc = instance.service
    svc.delete()
    logger.info(f'- deleted service {svc.name} of report {instance.report.name}')



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

