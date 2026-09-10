from django.db import models

from . import Course
from volume.models import Volume


class VolumeCourseBinding(models.Model):
    volume = models.ForeignKey(
        Volume,
        on_delete=models.CASCADE,
        related_name="coursebindings",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="volumebindings",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["volume", "course"],
                name="unique_course_volume_binding",
            ),
        ]

