import os
import logging

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from container.models import Image, Proxy
from project.models import Project


try:
    from kooplexhub.settings import KOOPLEX
except importerror:
    KOOPLEX = {}

logger = logging.getLogger(__name__)


class Report(models.Model):
    SC_PRIVATE = 'private'
    SC_INTERNAL = 'internal'
    SC_PUBLIC = 'public'
    SCOPE_LOOKUP = {
        SC_PRIVATE: 'private - Only the creator can view the report.',
        SC_INTERNAL: 'internal - The creator and collaborators can view the report.',
        SC_PUBLIC: 'public - Anyone can view the report.',
    }

    name = models.CharField(max_length = 200, null = False)
    is_static = models.BooleanField(default = True)
    description = models.TextField(max_length = 500, null = True, default = None)
    creator = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    created_at = models.DateTimeField(default = timezone.now)
    project = models.ForeignKey(Project, default=None, on_delete = models.CASCADE)
    folder = models.CharField(max_length = 200, null = False)
    index = models.CharField(max_length = 128, null = False)
    #thumbnail = models.CharField(max_length = 200, null = False) blob?

    scope = models.CharField(max_length = 16, choices = SCOPE_LOOKUP.items(), default = SC_PRIVATE)

    image = models.ForeignKey(Image, null = True, blank=True, on_delete = models.CASCADE) # what else than CASCADE?
    # To be able to sort (e.g. useful for courses)
    # tags = # useful if we wanna search according to keywords
    
    # password = models.CharField(max_length = 64, null = True, default = '', blank=True)

    @property
    def root(self):
        return "static" if self.is_static else "dynamic"

    class Meta:
        unique_together = [['project', 'folder']]


    @property
    def url(self):
        if self.is_static:
            return KOOPLEX['proxy'].get('url_report_static', 'http://localhost/{report.id}').format(report = self)
        else:
            from . import ReportContainerBinding
            rcb = ReportContainerBinding.objects.get(report=self)
            return Proxy.objects.get(image = self.image).path.format(container=rcb.container) #url_public(self)
            #return KOOPLEX['proxy'].get('url_report_dynamic', 'http://localhost/{report.id}').format(report = self)
