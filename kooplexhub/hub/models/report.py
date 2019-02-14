import os
import logging

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str, now, human_localtime

logger = logging.getLogger(__name__)

TYPE_LOOKUP = {
    'static': 'Static content served by an nginx server.',
    'bokeh': 'Dynamic content: runs a bokeh server behind the scene.',
    'dynamic': 'Dynamic content requires a running kernel in the back.',
    'service': 'Dynamic content requires a service implemented by user.',
}

class Report(models.Model):
    TP_STATIC = 'static'
    TP_BOKEH = 'bokeh'
    TP_DYNAMIC = 'dynamic'
    TP_SERVICE = 'service'
    TYPE_LIST = [ TP_STATIC, TP_DYNAMIC, TP_SERVICE, TP_BOKEH ]

    name = models.CharField(max_length = 200, null = False)
    description = models.TextField(max_length = 500, null = True, default = None)
    creator = models.ForeignKey(User, null = False)
    created_at = models.DateTimeField(default = timezone.now)
    folder = models.CharField(max_length = 200, null = False)

    reporttype = models.CharField(max_length = 16, choices = [ (x, TYPE_LOOKUP[x]) for x in TYPE_LIST ], default = TP_STATIC)
#TODO: scope: public, internal

    index = models.CharField(max_length = 128, null = False)
    password = models.CharField(max_length = 64, null = False)

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
        return os.path.join(KOOPLEX['base_url'], 'report', self.proxy_path, self.index)

    @property
    def url_external_latest(self):
        return os.path.join(KOOPLEX['base_url'], 'report', self.proxy_path_latest, self.index)

    @property
    def proxy_path(self):
        return os.path.join(self.creator.username, self.cleanname, self.ts_human)
        
    @property
    def proxy_path_latest(self):
        return os.path.join(self.creator.username, self.cleanname)

    def groupby(self):
        return [ r for r in Report.objects.filter(name = self.name, creator = self.creator) ]

    def latest(self):
        r_latest = None
        for r in self.groupby():
            if r_latest is None:
                r_latest = r
            elif r.created_at > r_latest.created_at:
                r_latest = r
        return r
              


@receiver(pre_save, sender = Report)
def snapshot_report(sender, instance, **kwargs):
    from kooplex.lib.filesystem import snapshot_report
    from kooplex.lib.proxy import addroute#, removeroute
    is_new = instance.id is None
    if not is_new:
        return
    instance.created_at = now()
    snapshot_report(instance)
    if instance.reporttype == Report.TP_STATIC:
        addroute(instance)

