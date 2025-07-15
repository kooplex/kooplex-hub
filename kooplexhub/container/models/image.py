from django.db import models

from hub.models import Thumbnail


class Image(models.Model):
    TP_PROJECT = 'projectimage'
    TP_REPORT = 'reportimage'
    TP_APP = 'appimage'
    TP_API = 'apiimage'
    TP_JOB = 'jobimage'
    TP_LOOKUP = {
        TP_PROJECT: 'project image',
        TP_REPORT: 'report image',
        TP_APP: 'app image',
        TP_API: 'api image',
        TP_JOB: 'job image',
    }
    name = models.CharField(max_length = 64, unique = True)
    present = models.BooleanField(default = True)
    imagetype = models.CharField(max_length = 32, choices = TP_LOOKUP.items(), default = TP_PROJECT)
    description = models.CharField(max_length = 250, default = "description missing")
    dockerfile = models.TextField(max_length = 4096)
    command = models.CharField(max_length = 250, default = "/entrypoint.sh")
    thumbnail = models.ForeignKey(Thumbnail, on_delete = models.CASCADE, default = None, null = True)

    def __str__(self):
        return self.name

    @property
    def hr(self):
        return self.name.split('/')[-1]

    @property
    def require_home(self):
        return self.imagetype == self.TP_PROJECT

    @property
    def mount_project(self):
        return self.imagetype == self.TP_PROJECT

    @property
    def mount_report(self):
        return True


