import os
import logging

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.apps import apps

from container.models import Image, Proxy 
from project.models import Project
#  from taggit.managers import TaggableManager

from hub.models import Thumbnail

from ..conf import REPORT_SETTINGS

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
    # which type of files to associate with?
    #list_of_extensions = ["py", "ipynb", "R", "html"]
    # where to look for the files?
    #search_dirs = ["","_build","_build/html/"] 

    def __str__(self):
        return self.name

class Report(models.Model):
    class Scope(models.TextChoices):
        PUBLIC = 'public', 'public - Anyone can view the report.'
        INTERNAL = 'internal', 'authenticated - An authenticated kooplex user can view the report.'
        PRIVATE = 'private', 'private - Only the creator can view the report.'
        COLLABORATION = 'collaboration', 'collaboration - The creator and collaborators can view the report.'


    name = models.CharField(max_length = 200, null = False)
    reporttype = models.ForeignKey(ReportType, default=1, on_delete = models.CASCADE)
#    is_static = models.BooleanField(default = True)
    description = models.TextField(max_length = 1000, null = True, default = None)
    creator = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    created_at = models.DateTimeField(default = timezone.now)
    project = models.ForeignKey(Project, default=None, on_delete = models.CASCADE)
    folder = models.CharField(max_length = 200, null = False)
    indexfile = models.CharField(max_length = 128, blank=True, null = True)
    thumbnail = models.ForeignKey(Thumbnail, on_delete=models.CASCADE, null=True, blank=True)
    scope = models.CharField(max_length = 16, choices = Scope.choices, default = Scope.PRIVATE)
    image = models.ForeignKey(Image, null = True, blank=True, on_delete = models.CASCADE) # what else than CASCADE?
#    tags = TaggableManager(blank = True)

    # To be able to sort (e.g. useful for courses)
    # tags = # useful if we wanna search according to keywords
    
    # password = models.CharField(max_length = 64, null = True, default = '', blank=True)

#    @property
#    def root(self):
#        return "static" if self.is_static else "dynamic"

    class Meta:
        unique_together = [['project', 'folder']]

    def save(self, *args, **kwargs):
        if self.thumbnail is None:
            first = Thumbnail.objects.order_by('pk').first()
            if first:
                self.thumbnail = first
        super().save(*args, **kwargs)

    @property
    def search(self):
       tags = ' '.join([ tag.name for tag in self.tags.all() ])
       return f'{self.name} {self.creator.profile.name} {tags}'.upper()

    @property
    def url(self):
        if self.image:
            # avoid circular import by loading the model lazily
            # FIXME: ? rcb = self.projectbindings.filter(report=self)
            try:
                RCB = apps.get_model('report', 'ReportContainerBinding')
                binding = RCB.objects.filter(report=self).select_related('container').first()
                return REPORT_SETTINGS['paths']['proxied'].format(container=binding.container)
            except LookupError:
                logger.exception("ReportContainerBinding model not found")
            except Exception:
                logger.exception("Error resolving ReportContainerBinding for report %s", self.pk)

        else:
            return REPORT_SETTINGS['paths']['static'].format(report = self)


