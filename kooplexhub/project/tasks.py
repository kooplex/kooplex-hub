import logging
import time

from channels.layers import get_channel_layer
from django_huey import db_task, task
from asgiref.sync import async_to_sync

from django.contrib.auth.models import User
from django.db import transaction

from hub.models import Group
from kooplexhub.settings import KOOPLEX
from hub.lib import archivedir, extracttarbal
from hub.lib import grantaccess_user, revokeaccess_user
from hub.lib import grantaccess_group, revokeaccess_group
from hub.lib import filename, dirname
from hub.lib import mkdir, archivedir, rmdir

logger = logging.getLogger(__name__)

@task(queue = 'project')
def grant_access(folders, acl):
    channel_layer=get_channel_layer()
    #FIXME: lehetne ACL: [{'folder': '...', 'groups_rw': [...], 'groups_ro': [...]}, ...]
    for f in folders:
        for gid in acl.get('groups_rw', []):
            with transaction.atomic():
                go = Group.objects.select_for_update().get(id = gid)
            grantaccess_group(go, f, readonly = False, recursive = True)
        for uid in acl.get('users_rw', []):
            grantaccess_user(User.objects.get(id = uid), f, readonly = False, recursive = True)

    async_to_sync(channel_layer.group_send)("project", {
            "type": "feedback",
            "feedback": f"Folders {folders} got acl {acl}",
        })
    return "Completed"

@task(queue = 'project')
def revoke_access(user_id, folders):
    u = User.objects.get(id = user_id)
    for f in folders:
        revokeaccess_user(u, f)
    async_to_sync(channel_layer.group_send)("project", {
            "type": "feedback",
            "feedback": f"{u}'s acls are removed from folders {folders}",
        })
    return "Completed"




