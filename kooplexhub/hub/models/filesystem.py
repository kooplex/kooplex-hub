import logging

from django.db import models
from django.contrib.auth.models import User
from ..models import Group

logger = logging.getLogger(__name__)

class FilesystemTask(models.Model):
    TSK_CREATE = 'c'
    TSK_GRANT_USER = 'gu'
    TSK_GRANT_GROUP = 'gg'
    TSK_REVOKE_USER = 'ru'
    TSK_REVOKE_GROUP = 'rg'
    TSK_TAR = 't'
    TSK_UNTAR = 'u'
    TSK_REMOVE = 'X'
    TSK_LOOKUP = {
        TSK_CREATE: 'Create a new folder',
        TSK_GRANT_USER: 'Grant filesystem rights to user',
        TSK_GRANT_GROUP: 'Grant filesystem rights to group',
        TSK_REVOKE_USER: 'Revoke filesystem rights from user',
        TSK_REVOKE_GROUP: 'Revoke filesystem right from group',
        TSK_TAR: 'Create a tarball',
        TSK_UNTAR: 'Extract a tarball',
        TSK_REMOVE: 'Remove a folder',
    }
    #issuer = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    folder = models.CharField(max_length = 256, null = True, default = None)
    tarbal = models.CharField(max_length = 256, null = True, default = None)
    grantee_user = models.ForeignKey(User, null = True, default = None, on_delete = models.CASCADE)
    readonly_user = models.BooleanField(default = False)
    grantee_group = models.ForeignKey(Group, null = True, default = None, on_delete = models.CASCADE)
    readonly_group = models.BooleanField(default = False)
    create_folder = models.BooleanField(default = False)
    remove_folder = models.BooleanField(default = False)
    task = models.CharField(max_length = 16, choices = TSK_LOOKUP.items())
    launched_at = models.DateTimeField(null = True, blank = True)
    stop_at = models.DateTimeField(null = True, blank = True)
    error = models.CharField(max_length = 256, null = True, default = None)
