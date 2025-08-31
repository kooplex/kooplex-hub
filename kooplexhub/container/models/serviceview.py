from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse

from hub.models import Thumbnail
from ..models import Image

class ServiceView(models.Model):
    from .proxy import Proxy
    name = models.CharField(max_length = 16, unique=True)
    proxy = models.ForeignKey(Proxy, on_delete = models.CASCADE, related_name='viewbindings')
    suffix = models.CharField(max_length = 128, null=True, blank=True)
    openable = models.BooleanField(default = True)
    pass_token = models.BooleanField(default = False)
    icon = models.ForeignKey(Thumbnail, on_delete = models.SET_NULL, null=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    @property
    def url(self):
        suffix=self.suffix or ""
        url=f"{self.proxy.hub_url}/{self.proxy.basepath}/{suffix}"
        return url if url.endswith('/') else url+'/'

    def url_substitute(self, container):
        return self.url.format(container = container)

