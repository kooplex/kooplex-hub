import os
import logging

from django.db import models

from container.models import Container
from ..models import Course

logger = logging.getLogger(__name__)

class CourseContainerBinding(models.Model):
    course = models.ForeignKey(Course, null = False, on_delete = models.CASCADE)
    container = models.ForeignKey(Container, null = False, on_delete = models.CASCADE)

    class Meta:
        unique_together = [['course', 'container']]

    def __str__(self):
        return "<CourseContainerBinding %s-%s>" % (self.course, self.container)


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
