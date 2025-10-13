import logging
import time

from channels.layers import get_channel_layer
from django_huey import db_task, task
from asgiref.sync import async_to_sync

from django.contrib.auth.models import User
from django.db import transaction

from hub.models import Group
from hub.lib import archivedir, extracttarbal
from hub.lib import grantaccess_user, revokeaccess_user
from hub.lib import grantaccess_group, revokeaccess_group
from hub.lib import mkdir, archivedir, rmdir

logger = logging.getLogger(__name__)

@task(queue = 'volume')
def grant_access(user, folder, can_write=False):
    grantaccess_user(user, folder, readonly = not can_write, recursive = True)
#    channel_layer=get_channel_layer()
#    async_to_sync(channel_layer.group_send)("project", {
#            "type": "feedback",
#            "feedback": f"Access granted on {folder}",
#        })
#    return "Completed"

#@task(queue = 'project')
#def revoke_access(user_id, folders):
#    u = User.objects.get(id = user_id)
#    for f in folders:
#        revokeaccess_user(u, f)
#    async_to_sync(channel_layer.group_send)("project", {
#            "type": "feedback",
#            "feedback": f"{u}'s acls are removed from folders {folders}",
#        })
#    return "Completed"




