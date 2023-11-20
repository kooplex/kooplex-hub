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
    # FIXME Delete in KOOPLEX.settings
    #path = models.CharField(max_length = 64, null = True, blank = True)
    # FIXME Delete in KOOPLEX.settings
    #path_open = models.CharField(max_length = 64, null = True, blank = True)
    image = models.ForeignKey(Image, null = False, on_delete = models.CASCADE)
    default = models.BooleanField(default = True)
    token_as_argument = models.BooleanField(default = False)
 
    class Meta:
        unique_together = [['image', 'name']]

    def proxy_route(self, container):
        return self.path.format(container = container) if self.path else None

# URL to the container
    def url_internal(self, container):
        return KOOPLEX['proxy'].get('url_internal', 'http://{container.label}:{proxy.port}').format(proxy = self, container = container, kubernetes_namespace = KOOPLEX['kubernetes']['namespace'])

# URL notebook server
    def url_container(self, container):
        return KOOPLEX['proxy'].get('url_notebook', 'http://localhost/notebook/{container.label}').format(container = container)

# URL notebook server
    def url_notebook(self, container):
        ide_suffix = container.env_variable("IDE_SUFFIX")
        return os.path.join(self.url_container(container), ide_suffix)

# # URL report
#     def url_report(self, container):
#         return os.path.join(KOOPLEX['proxy'].get('url_report', 'http://localhost/notebook/report/{container.label}').format(container = container))
