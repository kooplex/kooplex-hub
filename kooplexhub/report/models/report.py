import os
import logging

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from container.models import Image, Proxy 
from project.models import Project
from taggit.managers import TaggableManager

from hub.models import Thumbnail

try:
    from kooplexhub.settings import KOOPLEX
except importerror:
    KOOPLEX = {}

logger = logging.getLogger(__name__)

class ReportTag(models.Model):

    name = models.CharField(max_length = 40, null = False)

    def __str__(self):
        return self.name


class ReportType(models.Model):

    name = models.CharField(max_length = 40, null = False)
    #url_tag = models.CharField(max_length = 40, null = False) # For ingress to forward it to the right place
    is_static = models.BooleanField(default = True)
    description = models.TextField(max_length = 1000, null = True, default = None)
    #resourcetype_pic = models.ForeignKey(ResourceType, on_delete = models.CASCADE)

    def __str__(self):
        return self.name

class Report(models.Model):
    SC_PRIVATE = 'private'
    SC_COLLABORATION = 'collaboration'
    SC_INTERNAL = 'internal'
    SC_PUBLIC = 'public'
    SCOPE_LOOKUP = {
        SC_PRIVATE: 'private - Only the creator can view the report.',
        SC_COLLABORATION: 'collaboration - The creator and collaborators can view the report.',
        SC_INTERNAL: 'authenticated - An authenticated kooplex user can view the report.',
        SC_PUBLIC: 'public - Anyone can view the report.',
    }

    name = models.CharField(max_length = 200, null = False)
    reporttype = models.ForeignKey(ReportType, default=1, on_delete = models.CASCADE)
#    is_static = models.BooleanField(default = True)
    description = models.TextField(max_length = 1000, null = True, default = None)
    creator = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    created_at = models.DateTimeField(default = timezone.now)
    project = models.ForeignKey(Project, default=None, on_delete = models.CASCADE)
    folder = models.CharField(max_length = 200, null = False)
    indexfile = models.CharField(max_length = 128, blank=True, null = True)
    thumbnail = models.ForeignKey(Thumbnail, on_delete = models.CASCADE, default = None, null = True)


    scope = models.CharField(max_length = 16, choices = SCOPE_LOOKUP.items(), default = SC_PRIVATE)

    image = models.ForeignKey(Image, null = True, blank=True, on_delete = models.CASCADE) # what else than CASCADE?
    tags = TaggableManager(blank = True)

    # To be able to sort (e.g. useful for courses)
    # tags = # useful if we wanna search according to keywords
    
    # password = models.CharField(max_length = 64, null = True, default = '', blank=True)

#    @property
#    def root(self):
#        return "static" if self.is_static else "dynamic"

    class Meta:
        unique_together = [['project', 'folder']]


    @property
    def search(self):
       tags = ' '.join([ tag.name for tag in self.tags.all() ])
       return f'{self.name} {self.creator.profile.name} {tags}'.upper()

    @property
    def url(self):
        if self.reporttype.is_static:
            return KOOPLEX['proxy'].get('static_report_path_open', 'http://localhost/report/{report.id}/').format(report = self)
        else:
            from . import ReportContainerBinding
            rcb = ReportContainerBinding.objects.get(report=self)
            #return Proxy.objects.get(image = self.image).path_open.format(container=rcb.container) #url_public(self)
            #return KOOPLEX['environmental_variables']['REPORT_URL'].format(container=rcb.container) 
            return os.path.join(KOOPLEX['proxy'].get('report_path_open', 'http://localhost/{proxy.report_path_open}').format(container = rcb.container, report = self))

        #return KOOPLEX['proxy'].get('url_report', 'http://localhost/{report.id}').format(report = self, url_tag = url_tag)
            
        # if self.is_static:
        #     return KOOPLEX['proxy'].get('url_report_static', 'http://localhost/{report.id}').format(report = self)
        # else:
        #     from . import ReportContainerBinding
        #     rcb = ReportContainerBinding.objects.get(report=self)
        #     return Proxy.objects.get(image = self.image).path.format(container=rcb.container) #url_public(self)
        #     #return KOOPLEX['proxy'].get('url_report_dynamic', 'http://localhost/{report.id}').format(report = self)

