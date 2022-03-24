import logging
import os

from django.db import models

from .image import Image

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

KOOPLEX['proxy'].update({})

logger = logging.getLogger(__name__)

class Proxy(models.Model):
    name = models.CharField(max_length = 64, null = True)
    port = models.IntegerField(null = False)
    path = models.CharField(max_length = 64, null = True, blank = True)
    path_open = models.CharField(max_length = 64, null = True, blank = True)
    image = models.ForeignKey(Image, null = False, on_delete = models.CASCADE)
    default = models.BooleanField(default = True)
    token_as_argument = models.BooleanField(default = False)
 
    class Meta:
        unique_together = [['image', 'name']]

    def proxy_route(self, container):
        return self.path.format(container = container) if self.path else None

    def url_internal(self, container):
        return KOOPLEX['proxy'].get('url_internal', 'http://{container.label}:{proxy.port}').format(container = container, proxy = self)

    def url_public(self, container):
        return KOOPLEX['proxy'].get('url_public', 'http://localhost/{proxy.path_open}').format(proxy = self).format(container = container)

