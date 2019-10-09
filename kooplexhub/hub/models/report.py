import os
import logging

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from django.contrib.auth.models import User
from django.dispatch import receiver

from .image import Image

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str, now, human_localtime

logger = logging.getLogger(__name__)

TYPE_LOOKUP = {
    'static': 'HTML - content hosted on a webserver.',
    'bokeh': 'BOKEH - an interactive applications, runs served by a bokeh.',
    'dynamic': 'NB - A jupyter notebook.',
    'service': 'API - A REST API run in a notebook.',
}

SCOPE_LOOKUP = {
    'private': 'private - Only the creator can view the report.',
    'internal': 'internal - The creator and collaborators can view the report.',
    'public': 'public - Anyone can view the report.',
}

class Report(models.Model):
    TP_STATIC = 'static'
    TP_BOKEH = 'bokeh'
    TP_DYNAMIC = 'dynamic'
    TP_SERVICE = 'service'
    TYPE_LIST = [ TP_STATIC, TP_DYNAMIC, TP_SERVICE, TP_BOKEH ]

    SC_PRIVATE = 'private'
    SC_INTERNAL = 'internal'
    SC_PUBLIC = 'public'
    SCOPE_LIST = [ SC_PRIVATE, SC_INTERNAL, SC_PUBLIC ]

    name = models.CharField(max_length = 200, null = False)
    description = models.TextField(max_length = 500, null = True, default = None)
    creator = models.ForeignKey(User, null = False)
    created_at = models.DateTimeField(default = timezone.now)
    folder = models.CharField(max_length = 200, null = False)

    reporttype = models.CharField(max_length = 16, choices = [ (x, TYPE_LOOKUP[x]) for x in TYPE_LIST ], default = TP_STATIC)
    scope = models.CharField(max_length = 16, choices = [ (x, SCOPE_LOOKUP[x]) for x in SCOPE_LIST ], default = SC_INTERNAL)

    image = models.ForeignKey(Image, null = True)
    # To be able to sort (e.g. useful for courses)
    directory_name = models.CharField(max_length = 50, null = False, default='default')
    
    index = models.CharField(max_length = 128, null = False)
    password = models.CharField(max_length = 64, null = True, default = '')

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
        #FIXME worng urls e.g. service
        if self.reporttype == self.TP_STATIC:
            return os.path.join(KOOPLEX['base_url'], 'report', self.proxy_path, self.index)
        elif self.reporttype == self.TP_BOKEH:
            return os.path.join(KOOPLEX['base_url'], 'report', self.proxy_path, self.index)
        elif self.reporttype == self.TP_DYNAMIC:
            return os.path.join(KOOPLEX['base_url'], 'report', self.proxy_path, self.index)
        elif self.reporttype == self.TP_SERVICE:
            #https://kooplex-test.elte.hu/notebook/report-jegesm-simpleapi-20190827-101002/report/help 
            return os.path.join(KOOPLEX['base_url'], 'notebook', self.proxy_path, self.index, 'report/help')

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

    @property
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
    from kooplex.lib.filesystem import snapshot_report, prepare_dashboardreport_withinitcell
    from kooplex.lib.proxy import addroute#, removeroute
    is_new = instance.id is None
    if not is_new:
        return
    instance.created_at = now()
    snapshot_report(instance)
    if instance.reporttype == instance.TP_DYNAMIC:
        prepare_dashboardreport_withinitcell(instance)
    if instance.reporttype == Report.TP_STATIC:
        addroute(instance)


@receiver(pre_delete, sender = Report)
def garbage_report(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbage_report
    from kooplex.lib.proxy import addroute, removeroute
    garbage_report(instance)
    if instance.reporttype == Report.TP_STATIC and instance != instance.latest:
        addroute(instance.latest)
    removeroute(instance)

