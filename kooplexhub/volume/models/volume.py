import logging
import re
import os

from django.db import models

logger = logging.getLogger(__name__)

class Volume(models.Model):
    name = models.CharField(max_length = 64, unique = True)
    description = models.TextField(null = True)
    claim = models.CharField(max_length = 64)
    subPath = models.CharField(max_length = 64, null = True)
    #readonly_gid = models.IntegerField() # even better foreignkey(group)
    #readwrite_gid = models.IntegerField()
    is_present = models.BooleanField(default = True)

    def __str__(self):
        return "Volume {} {}".format(self.name, self.path)

    @staticmethod
    def list_volumes(user):
        raise NotImplementedError("""
#TODO        return Volume.objects.filter(readonly_gid__in = user.gids).extend(readwrite_gid__in = user.gids).unique()
        """)
