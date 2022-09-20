from celery import shared_task
#import logging
import time

from django.contrib.auth.models import User
from django.db import transaction

from hub.models import Group
from kooplexhub.settings import KOOPLEX
from hub.lib import archivedir, extracttarbal
from hub.lib import grantaccess_user, revokeaccess_user
from hub.lib import grantaccess_group, revokeaccess_group
from hub.lib import filename, dirname
from hub.lib import mkdir, archivedir, rmdir

#logger = logging.getLogger(__name__)
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

@shared_task()
def manage_folder(create_folder, folders, acl):
    for f in folders:
        if create_folder:
            mkdir(f)
        for gid in acl.pop('groups_rw', []):
            with transaction.atomic():
                go = Group.objects.select_for_update().get(id = gid)
            grantaccess_group(go, f, readonly = False, recursive = True)
        for uid in acl.pop('users_rw', []):
            grantaccess_user(User.objects.get(id = uid), f, readonly = False, recursive = True)


@shared_task()
def revoke_access(user_id, folders):
    for f in folders:
        revokeaccess_user(User.objects.get(id = user_id), f)


@shared_task()
def garbage(project_folder, project_tarbal, report_prepare_folder):
    rmdir(report_prepare_folder)
    archivedir(project_folder, project_tarbal, remove = True)


