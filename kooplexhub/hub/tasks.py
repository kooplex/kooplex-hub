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


@db_task(queue="hub")
def continue_user_delete(
    user_id,
):
    try:
        complete = progress_user_delete(
            user_id=user_id
        )

    except Exception as error:
        mark_user_delete_failed(
            user_id=user_id,
            error=error,
        )
        raise

    if not complete:
        raise RetryTask(delay=2)



@task(queue = 'hub')
def delete_folder(folder):
    logging.warning(f'Deleting folder {folder}')
    rmdir( folder )


@task(queue = 'hub')
def archive(folder, tarbal, remove=False):
    archivedir(folder, tarbal, remove = remove)
