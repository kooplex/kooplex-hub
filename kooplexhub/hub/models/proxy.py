import logging
import os

from django.db import models

from .serviceenvironment import ServiceEnvironment

logger = logging.getLogger(__name__)

class Proxy(models.Model):
    env_prefix = models.CharField(max_length = 64, null = True)
    port = models.IntegerField(null = False)
    path = models.CharField(max_length = 64, null = True)
    is_hub_entry = models.BooleanField(null = False)
    serviceenvironment = models.ForeignKey(ServiceEnvironment, null = False)
 
    @property
    def url(self): #FIXME: rename url_internal
        return f'http://{self.serviceenvironment.name}:{self.port}/{self.path}'

    @property
    def url_public(self):
        fqdn = os.environ.get('DOMAIN', 'localhost')
        return f'https://{fqdn}/{self.path}'

    @property
    def env_variables(self):
        if self.env_prefix:
            yield { 'name': f'{self.env_prefix}_URL', 'value': self.path }
            yield { 'name': f'{self.env_prefix}_PORT', 'value': str(self.port) }

