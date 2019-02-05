import logging
import datetime
import requests
import time

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str, now

logger = logging.getLogger(__name__)

TYPE_LOOKUP = {
    'static': 'Static content served by an nginx server.',
    'dynamic': 'Dynamic content requires a running kernel in the back.',
    'service': 'Dynamic content requires a service implemented by user.',
}

class Report(models.Model):
    TP_STATIC = 'static'
    TP_DYNAMIC = 'dynamic'
    TP_SERVICE = 'service'
    TYPE_LIST = [ TP_STATIC, TP_DYNAMIC, TP_SERVICE ]

    name = models.CharField(max_length = 200, null = False)
    creator = models.ForeignKey(User, null = False)
    created_at = models.DateTimeField(default = timezone.now)

    reporttype = models.CharField(max_length = 16, choices = [ (x, TYPE_LOOKUP[x]) for x in TYPE_LIST ], default = TP_STATIC)
#TODO: scope: public, internal

    index = models.CharField(max_length = 128, null = False)
    password = models.CharField(max_length = 64, null = False)

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return "<Report %s@%s>" % (self.name, self.creator)


#@receiver(pre_save, sender = Container)
#def container_image_change(sender, instance, **kwargs):
#    is_new = instance.id is None
#    old_instance = Container() if is_new else Container.objects.get(id = instance.id)
#    if not is_new and old_instance.image != instance.image:
#         instance.marked_to_remove = True

