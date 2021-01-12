import logging

from django.db import models

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Image(models.Model):
    TP_PROJECT = 'projectimage'
    TP_REPORT_HTML = 'nginximage'
    TP_REPORT_BOKEH = 'bokehimage'
    TP_REPORT_PLOTLY = 'plotlyimage'
    TP_REPORT_JKGW = 'jkgwimage'
    TP_REPORT_SHINY = 'shinyimage'
    TP_API = 'apiimage'
    TP_LOOKUP = {
        TP_PROJECT: 'project image',
        TP_REPORT_HTML: 'nginx image for html reports',
        TP_REPORT_BOKEH: 'bokeh report image',
        TP_REPORT_PLOTLY: 'plotly report image',
        TP_REPORT_JKGW: 'jupyter kernel gateway report image',
        TP_REPORT_SHINY: 'R shiny report image',
        TP_API: 'api image',
    }
    name = models.CharField(max_length = 32)
    present = models.BooleanField(default = True)
    imagetype = models.CharField(max_length = 32, choices = TP_LOOKUP.items(), default = TP_PROJECT)
    description = models.CharField(max_length = 250, default="description missing")
    dockerfile = models.TextField(max_length = 4096)

    def __str__(self):
        return self.name

    @property
    def imagename(self):
        return KOOPLEX.get('docker', {}).get('pattern_imagename', 'image-%(imagename)s') % { 'imagename': self.name }

    @property
    def require_home(self):
        return self.imagetype == self.TP_PROJECT

    @property
    def mount_project(self):
        return self.imagetype == self.TP_PROJECT

    @property
    def mount_report(self):
        return True
