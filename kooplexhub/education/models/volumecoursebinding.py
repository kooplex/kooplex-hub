import logging

from django.contrib.auth.models import User
from django.db import models

from . import Course
from volume.models import Volume

logger = logging.getLogger(__name__)


class VolumeCourseBinding(models.Model):
    volume = models.ForeignKey(Volume, on_delete = models.CASCADE, null = False)
    course = models.ForeignKey(Course, on_delete = models.CASCADE, null = False)

    class Meta:
        unique_together = [['volume', 'course']]

