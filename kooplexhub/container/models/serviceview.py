from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse

from hub.models import Thumbnail
from ..models import Image

class ServiceView(models.Model):
    from .proxy import Proxy
    name = models.CharField(max_length = 16, unique=True)
    proxy = models.ForeignKey(Proxy, on_delete = models.CASCADE, null=False)
    suffix = models.CharField(max_length = 128)
    openable = models.BooleanField(default = True)
    pass_token = models.BooleanField(default = False)
    icon = models.ForeignKey(Thumbnail, on_delete = models.SET_NULL, null=True)

    def __str__(self):
        return self.name

    @property
    def url(self):
        return f"{self.proxy.hub_url}/{self.proxy.basepath}/{self.suffix}"

    def url_substitute(self, container):
        return self.url.format(container = container)

    # rendering logic
    def render_open_html(self, container, show_name=False):
        if not self.openable or not getattr(container, 'id', None):
            return ""
        _link = reverse('container:open_serviceview', args = [container.id, self.id])
        return render_to_string("widgets/widget_container_open.html", {"container": container, "view": self, "link": _link, "show_name": show_name})

