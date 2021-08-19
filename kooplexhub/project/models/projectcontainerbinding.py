import os
import logging

from django.db import models

from container.models import Container
from ..models import Project

logger = logging.getLogger(__name__)

class ProjectContainerBinding(models.Model):
    project = models.ForeignKey(Project, on_delete = models.CASCADE, null = False)
    container = models.ForeignKey(Container, on_delete = models.CASCADE, null = False)

    def __str__(self):
        return f"<ProjectContainerBinding {self.project}-{self.container}>"



####
####
####
####class ReportContainerBinding(models.Model):
####    report = models.ForeignKey(Report, null = False)
####    service = models.ForeignKey(Container, null = False)
####
####    def __str__(self):
####        return f"<ReportContainerBinding {self.report}-{self.service}>"
####
####@receiver(post_save, sender = Report)
####def create_report_service(sender, instance, created, **kwargs):
####    if created:
####        svc = Container.objects.create(name = instance.cleanname, user = instance.creator, suffix = 'report', image = instance.image)
####        logger.info(f'+ created service {svc.name} for report {instance.name}')
####        ReportContainerBinding.objects.create(report = instance, service = svc)
####        svc.start()
####        logger.info(f'started report service {svc.label}')
####
####@receiver(post_delete, sender = ReportContainerBinding)
####def remove_report_service(sender, instance, **kwargs):
####    svc = instance.service
####    svc.delete()
####    logger.info(f'- deleted service {svc.name} of report {instance.report.name}')



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

