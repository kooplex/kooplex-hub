import logging

from django.db import models

from .report import Report
from container.models import Container

logger = logging.getLogger(__name__)


class ReportContainerBinding(models.Model):
    report = models.ForeignKey(Report, on_delete = models.CASCADE, null = False)
    container = models.ForeignKey(Container, on_delete = models.CASCADE, null = False)

    class Meta:
        unique_together = [['report', 'container']]
