import os
import logging

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from django.contrib.auth.models import User
from django.dispatch import receiver

from .project import Project
from .image import Image

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str, now, human_localtime, add_report_nginx_api, remove_report_nginx_api

logger = logging.getLogger(__name__)



class Report(models.Model):
    #FIXME: ennek van értelme még?
    SC_PRIVATE = 'private'
    SC_INTERNAL = 'internal'
    SC_PUBLIC = 'public'
    SC_LOOKUP = {
        SC_PRIVATE: 'private - Only the creator can view the report.',
        SC_INTERNAL: 'internal - The creator and collaborators can view the report.',
        SC_PUBLIC: 'public - Anyone can view the report.',
    }
    name = models.CharField(max_length = 200, null = False)
    description = models.TextField(max_length = 500, null = True, default = None)
    creator = models.ForeignKey(User, null = False)
    project = models.ForeignKey(Project, null = False)
    scope = models.CharField(max_length = 16, choices = SC_LOOKUP.items(), default = SC_INTERNAL)
    created_at = models.DateTimeField(default = timezone.now)
    image = models.ForeignKey(Image, null = False)

    folder = models.CharField(max_length = 200, null = False)
    index = models.CharField(max_length = 128, null = False)

    password = models.CharField(max_length = 64, null = True, default = '', blank=True)

    class Meta:
        unique_together = [['name']]


    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return "<Report %s@%s>" % (self.name, self.creator)

    @property
    def cleanname(self):
        return standardize_str(self.name)

    @property
    def ts_human(self):
        return human_localtime(self.created_at)

    @property
    def url_external(self):
        from .service import ReportServiceBinding
        svc = ReportServiceBinding.objects.get(report = self).service
        return svc.default_proxy.url_public(svc)



@receiver(pre_save, sender = Report)
def snapshot_report(sender, instance, **kwargs):
    from kooplex.lib.filesystem import snapshot_report
    is_new = instance.id is None
    if not is_new:
        return
    instance.created_at = now()
    snapshot_report(instance)


@receiver(pre_delete, sender = Report)
def garbage_report(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbage_report
    garbage_report(instance)



#TODO: make use of it
###class ReportTag(models.Model):
###    name = models.CharField(max_length = 200, null = False)
###    report = models.ForeignKey(Report, null = False)


