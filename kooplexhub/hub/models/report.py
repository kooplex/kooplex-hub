import os
import logging

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from django.contrib.auth.models import User
from django.dispatch import receiver

from .image import Image

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str, now, human_localtime, add_report_nginx_api, remove_report_nginx_api

logger = logging.getLogger(__name__)

TYPE_LOOKUP = {
    'static': 'HTML - content hosted on a webserver.',
    'bokeh': 'BOKEH - an interactive applications, served by a bokeh.',
    'plotly_dash': 'Plotly Dash - an interactive applications, served by a dash server.',
    'dynamic': 'NB - A jupyter notebook.',
    'service': 'API - A REST API run in a notebook.',
    'shiny': 'R - shiny application',
    'plot_server': 'Dashboard and an API for remote embedding',
}

SCOPE_LOOKUP = {
    'private': 'private - Only the creator can view the report.',
    'internal': 'internal - The creator and collaborators can view the report.',
    'public': 'public - Anyone can view the report.',
}

class Report(models.Model):
    TP_STATIC = 'static'
    TP_BOKEH = 'bokeh'
    TP_DASH = 'plotly_dash'
    TP_DYNAMIC = 'dynamic'
    TP_SERVICE = 'service'
    TP_SHINY = 'shiny'
    TP_PLOTSERVER = 'plot_server'
    TYPE_LIST = [ TP_STATIC, TP_DYNAMIC, TP_SERVICE, TP_BOKEH, TP_DASH, TP_SHINY, TP_PLOTSERVER ]

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

    image = models.ForeignKey(Image, null = True, blank=True)
    # To be able to sort (e.g. useful for courses)
    subcategory_name = models.CharField(max_length = 50, null = False, default='default', blank=True)
    tag_name = models.CharField(max_length = 50, null = False, default='default', blank=True)
    
    index = models.CharField(max_length = 128, null = False)
    password = models.CharField(max_length = 64, null = True, default = '', blank=True)

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return "<Report %s@%s>" % (self.name, self.creator)

    @property
    def cleanname(self):
        return standardize_str(self.name)

    @property
    def cleansubcategory_name(self):
        return 'default' if self.subcategory_name else standardize_str(self.subcategory_name)

    @property
    def cleantag_name(self):
        return '' if self.tag_name == '' else standardize_str(self.tag_name)

    @property
    def ts_human(self):
        return human_localtime(self.created_at)

    @property
    def container_name(self):
        container_name_dict = {
                'un': self.creator.username, 
                'rn': self.cleanname,
                'tn': self.cleantag_name,
#                'ts': self.ts_human.replace(':', '').replace('_', '')
                }
        return 'report-%(un)s-%(rn)s-%(tn)s' % container_name_dict

    @property
    def url_external(self):
        #FIXME wrong urls e.g. service
        if self.reporttype == self.TP_STATIC:
            return os.path.join(KOOPLEX['base_url'], 'report', self.proxy_path, self.index)
        elif self.reporttype == self.TP_BOKEH:
            return "http://%s:8000"%self.container_name
        elif self.reporttype == self.TP_DYNAMIC:
            return os.path.join(KOOPLEX['base_url'], 'report', self.proxy_path, self.index)
        elif self.reporttype == self.TP_SERVICE or self.reporttype == self.TP_PLOTSERVER:
            #https://kooplex-test.elte.hu/notebook/report-jegesm-simpleapi-20190827-101002/report/help 
            return os.path.join(KOOPLEX['base_url'], 'notebook', self.proxy_path, self.index, 'report/help')
        elif self.reporttype == self.TP_SHINY:
            return os.path.join(KOOPLEX['base_url'], 'shiny', self.proxy_path)

    @property
    def url_external_latest(self):
        if self.reporttype == Report.TP_STATIC:
            return os.path.join(KOOPLEX['base_url'], 'report', self.proxy_path_latest, self.index)
        elif self.reporttype == self.TP_SHINY:
            return os.path.join(KOOPLEX['base_url'], 'shiny', self.proxy_path_latest)
        else:
            return os.path.join(KOOPLEX['base_url'], 'notebook', self.proxy_path_latest, 'report')

    @property
    def proxy_path(self):
        if self.cleantag_name == '':
            return self.proxy_path_latest
        else:
            return os.path.join(self.creator.username, self.cleanname, self.cleantag_name)

    @property
    def proxy_path_latest(self):
        if self.reporttype == Report.TP_STATIC or self.reporttype == Report.TP_SHINY:
            return os.path.join(self.creator.username, self.cleanname, 'latest')
        else:
            container_name_dict = {
                    'un': self.creator.username,
                    'rn': self.cleanname,
                    }
            return 'report-%(un)s-%(rn)s' % container_name_dict


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
        if instance.password:
            add_report_nginx_api(instance)
    if instance.reporttype == Report.TP_BOKEH or instance.reporttype == Report.TP_SHINY:
        addroute(instance)


@receiver(pre_delete, sender = Report)
def garbage_report(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbage_report
    from kooplex.lib.proxy import addroute, removeroute
    garbage_report(instance)
    if instance.password:
        remove_report_nginx_api(instance)
    removeroute(instance)
    if instance.reporttype != Report.TP_DYNAMIC and instance == instance.latest:
       removeroute(instance.latest)

