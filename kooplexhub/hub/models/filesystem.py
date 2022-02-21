import logging

from django.db import models
from django.contrib.auth.models import User
from ..models import Group

logger = logging.getLogger(__name__)

class FilesystemTask(models.Model):
    TSK_CREATE = 'c'
    TSK_GRANT = 'g'
    TSK_REVOKE = 'r'
    TSK_TAR = 't'
    TSK_UNTAR = 'u'
    TSK_REMOVE = 'X'
    TSK_LOOKUP = {
        TSK_CREATE: 'Create a new folder',
        TSK_GRANT: 'Grant filesystem rights',
        TSK_REVOKE: 'Revoke filesystem rights',
        TSK_TAR: 'Create a tarball',
        TSK_UNTAR: 'Extract a tarball',
        TSK_REMOVE: 'Remove a folder',
    }
    #issuer = models.ForeignKey(User, null = False, on_delete = models.CASCADE, default = None)
    folder = models.CharField(max_length = 256, null = True, default = None)
    tarbal = models.CharField(max_length = 256, null = True, default = None)
    users_rw = models.CharField(max_length = 256, null = True, default = None, blank = True)
    users_ro = models.CharField(max_length = 256, null = True, default = None, blank = True)
    groups_rw = models.CharField(max_length = 256, null = True, default = None, blank = True)
    groups_ro = models.CharField(max_length = 256, null = True, default = None, blank = True)
    create_folder = models.BooleanField(default = False)
    remove_folder = models.BooleanField(default = False)
    recursive = models.BooleanField(default = False)
    task = models.CharField(max_length = 16, choices = TSK_LOOKUP.items())
    launched_at = models.DateTimeField(null = True, blank = True)
    stop_at = models.DateTimeField(null = True, blank = True)
    error = models.CharField(max_length = 256, null = True, default = None)
