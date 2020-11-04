import logging
import os

from django.db import models

from .image import Image

logger = logging.getLogger(__name__)

class Proxy(models.Model):
    name = models.CharField(max_length = 64, null = True)
    port = models.IntegerField(null = False)
    path = models.CharField(max_length = 64, null = True)
    image = models.ForeignKey(Image, null = False)
    default = models.BooleanField(default = True)
 
    def proxy_route(self, service):
        return self.path.format(service = service)

    def url_internal(self, service):
        return f'http://{service.name}:{self.port}'

    def url_public(self, service):
        fqdn = os.environ.get('DOMAIN', 'localhost')
        return f'https://{fqdn}/{self.path}'.format(service = service)
