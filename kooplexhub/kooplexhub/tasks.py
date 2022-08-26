from celery import shared_task
import logging
import time

from django.contrib.auth.models import User
from hub.models import Group
from hub.lib import mkdir, rmdir
from hub.lib import archivedir, extracttarbal
from hub.lib import grantaccess_user, revokeaccess_user
from hub.lib import grantaccess_group, revokeaccess_group

logger = logging.getLogger(__name__)


@shared_task()
def create_folders(folders = [], grant_useraccess = {}, grant_groupaccess = {}):
    for folder in folders:
        mkdir(folder)
    for user_id, folder_tups in grant_useraccess.items():
        user = User.objects.get(id = user_id)
        for folder, readonly, recursive in folder_tups:
            grantaccess_user(user, folder, readonly, recursive)
    for group_id, folder_tups in grant_useraccess.items():
        group = Group.objects.get(id = group_id)
        for folder, readonly, recursive in folder_tups:
            grantaccess_group(user, folder, readonly, recursive)


@shared_task()
def delete_folders(folders = [], archives = {}, revoke_useraccess = {}, revoke_groupaccess = {}):
    for folder in folders:
        rmdir(folder)
    for tarbal, folder in archives.items():
        archivedir(folder, tarbal, remove = True)
    for user_id, folders in revoke_useraccess.items():
        user = User.objects.get(id = user_id)
        for folder in folders:
            revokeaccess_user(user, folder)
    for group_id, folders in revoke_groupaccess.items():
        group = Group.objects.get(id = group_id)
        for folder in folders:
            revokeaccess_group(group, folder)


@shared_task()
def create_tar(folder, tarbal, remove_folder = False):
    archivedir(folder, tarbal, remove = remove_folder)


@shared_task()
def extract_tar(tarbal, folder, recursive = False, users_rw = [], users_ro = []):
    extracttarbal(tarbal, folder)
    for u in users_ro:
        grantaccess_user(User.objects.get(id = u), folder, readonly = True, recursive = recursive)
    for u in users_rw:
        grantaccess_user(User.objects.get(id = u), folder, recursive = recursive)









@shared_task()
def task_do_something(vmi):
    with open('/tmp/retek.dat', 'a') as f:
        f.write("alma " + vmi + ' ' + __name__ + '\n')
    logger.info("KALL, waiting to mimic heavy load")
    time.sleep(20)
    logger.info("READY")
