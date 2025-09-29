import logging
import time

from channels.layers import get_channel_layer
from django_huey import db_task, task
from asgiref.sync import async_to_sync

from django.contrib.auth.models import User

from hub.lib import archivedir, extracttarbal, grantaccess_user
from hub.lib import mkdir, archivedir, rmdir
from hub.fs import userhome, usergarbage, userscratch, userhome_garbage

from container.conf import CONTAINER_SETTINGS
from .conf import HUB_SETTINGS

logger = logging.getLogger(__name__)

@task(queue = 'hub')
def delete_folder(folder):
    logging.warning(f'Deleting folder {folder}')
    rmdir( folder )


@task(queue = 'hub')
def garbage_home(user_id):
    user = User.objects.get(id = user_id)
    rmdir( usergarbage(user) )
    if CONTAINER_SETTINGS['mounts']['scratch'] is not None:
        rmdir( userscratch(user) )
    if HUB_SETTINGS['archive_home']:
        archivedir( userhome(user), userhome_garbage(user), remove = True)
    else:
        rmdir( userhome(user) )


@task(queue = 'hub')
def archive(folder, tarbal, remove=False):
    archivedir(folder, tarbal, remove = remove)
