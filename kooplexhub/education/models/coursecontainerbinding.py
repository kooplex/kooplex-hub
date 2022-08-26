import os
import logging

from django.db import models

from container.models import Container
from education.models import Course

logger = logging.getLogger(__name__)

class CourseContainerBinding(models.Model):
    course = models.ForeignKey(Course, null = False, on_delete = models.CASCADE)
    container = models.ForeignKey(Container, null = False, on_delete = models.CASCADE)

    class Meta:
        unique_together = [['course', 'container']]

    def __str__(self):
        return "<CourseContainerBinding %s-%s>" % (self.course, self.container)


