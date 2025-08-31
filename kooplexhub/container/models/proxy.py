import os

from django.db import models

from .image import Image

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

try:
    from kooplexhub.settings import proto
except ImportError:
    proto = 'https'


class Proxy(models.Model):
    name = models.CharField(max_length = 64, null = True)
    basepath = models.CharField(max_length = 64, null = False, default='notebook/{container.label}')
    register = models.BooleanField(default = True)
    svc_proto = models.CharField(max_length = 8, choices = map(lambda x:(x,x), ['http', 'https']), default = 'http')
    svc_hostname = models.CharField(max_length = 64, null = False, default='{container.label}')
    svc_port = models.IntegerField(null = False)

    def __str__(self):
        return f"<Proxy: {self.name} reg:{self.register} basepath:{self.basepath}>"


    @property
    def proto(self):
        return KOOPLEX.get('proxy', {}).get('proto', 'https')

    @property
    def fqdn(self):
        from kooplexhub.settings import SERVERNAME as FQDN
        return FQDN

    @property
    def svc_dn(self):
        ns=KOOPLEX.get('kubernetes', {}).get('namespace', 'default')
        return f"{self.svc_hostname}.{ns}"

    @property
    def svc_endpoint(self): 
        return f"{self.svc_proto}://{self.svc_dn}:{self.svc_port}/"

    @property
    def hub_url(self):
        return f"{proto}://{self.fqdn}"

    @property
    def views(self):
        return self.viewbindings.all()

    def addroute(self, container):
        from ..lib.proxy import addroute
        if not self.register:
            return
        addroute(self.basepath.format(container = container), self.svc_endpoint.format(container=container))
        

    def removeroute(self, container):
        from ..lib.proxy import removeroute
        removeroute(self.basepath.format(container = container))


class ProxyImageBinding(models.Model):
    from .image import Image
    proxy = models.ForeignKey(Proxy, on_delete = models.CASCADE, related_name = 'imagebindings')
    image = models.ForeignKey(Image, on_delete = models.CASCADE, related_name = 'proxybindings')

    class Meta:
        unique_together = [['image', 'proxy']]
